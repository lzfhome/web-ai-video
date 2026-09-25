import asyncio
import base64
import json
import os
import shutil
import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ark_client
from config import CONFIG
from store import TaskStore, ChainJobStore, ExtendJobStore, ImageJobStore, public_task
import volc_usage

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
VIDEO_DIR = DATA_DIR / "videos"
UPLOAD_DIR = DATA_DIR / "uploads"
STATIC_DIR = ROOT / "static"

V_AI_DIR = DATA_DIR / "gen_videos"
V_CUT_DIR = DATA_DIR / "cut_videos"
UP_IMG_DIR = DATA_DIR / "gen_images"
UP_FRAME_DIR = DATA_DIR / "cut_frames"
UP_REF_DIR = DATA_DIR / "refs"

MOVE_BASE = Path("/home/oliver/workspace/AIWork/ai-learning")
MOVE_ROOT = MOVE_BASE / "lzf"

TASKS_FILE = DATA_DIR / "tasks.json"
CHAIN_FILE = DATA_DIR / "chain_jobs.json"
EXTEND_FILE = DATA_DIR / "extend_jobs.json"
IMAGE_JOBS_FILE = DATA_DIR / "image_jobs.json"
POLL_INTERVAL = 5

ACTIVE_STATUS = {"queued", "running", "pending"}
TERMINAL_STATUS = {"succeeded", "failed", "expired", "cancelled"}

PROMPTS_LOG = DATA_DIR / "prompts.jsonl"


def _log_prompt(kind: str, model: str, prompt: str, ref: str = ""):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(PROMPTS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "time": int(time.time()),
                "kind": kind,
                "model": model,
                "prompt": prompt[:4000],
                "ref": ref,
            }, ensure_ascii=False) + "\n")
    except OSError:
        pass

store = TaskStore(str(TASKS_FILE))
chain_store = ChainJobStore(str(CHAIN_FILE))
extend_store = ExtendJobStore(str(EXTEND_FILE))
image_job_store = ImageJobStore(str(IMAGE_JOBS_FILE))

VALID_TYPES = {"text", "image_url", "video_url", "audio_url"}
VALID_ROLES = {"first_frame", "last_frame", "reference_image", "reference_video", "reference_audio"}
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


class ContentItem(BaseModel):
    type: str
    text: str | None = None
    image_url: dict | None = None
    video_url: dict | None = None
    audio_url: dict | None = None
    role: str | None = None


class CreateTaskRequest(BaseModel):
    model: str = Field(default=CONFIG["default_model"])
    content: list[ContentItem]
    resolution: str = Field(default=CONFIG["defaults"]["resolution"])
    ratio: str = Field(default=CONFIG["defaults"]["ratio"])
    duration: int = Field(default=CONFIG["defaults"]["duration"])
    seed: int = Field(default=CONFIG["defaults"]["seed"])
    camera_fixed: bool = Field(default=CONFIG["defaults"]["camera_fixed"])
    watermark: bool = Field(default=CONFIG["defaults"]["watermark"])
    generate_audio: bool = Field(default=CONFIG["defaults"]["generate_audio"])
    omni_reference_task_type: str = Field(default=CONFIG["defaults"].get("task_type", "auto"))


class ChainItem(BaseModel):
    prompt: str = ""
    image: str = ""
    duration: int = -1


class CreateChainRequest(BaseModel):
    items: list[ChainItem]
    model: str = Field(default=CONFIG["default_model"])
    resolution: str = Field(default=CONFIG["defaults"]["resolution"])
    ratio: str = Field(default=CONFIG["defaults"]["ratio"])
    duration: int = Field(default=CONFIG["defaults"]["duration"])
    seed: int = Field(default=CONFIG["defaults"]["seed"])
    camera_fixed: bool = Field(default=CONFIG["defaults"]["camera_fixed"])
    watermark: bool = Field(default=CONFIG["defaults"]["watermark"])
    generate_audio: bool = Field(default=CONFIG["defaults"]["generate_audio"])
    chain: bool = True


class StoryboardRequest(BaseModel):
    story: str
    count: int = 1
    model: str = ""


class ImageJobRequest(BaseModel):
    model: str = Field(default=CONFIG["default_model"])
    prompts: list[str]
    size: str = "2560x1440"
    watermark: bool = False
    references: list[str] = []
    sequential: bool = False


class ExtendJobRequest(BaseModel):
    model: str = Field(default=CONFIG["default_model"])
    video_url: str
    prompt: str = "向后延长 @视频1，保持画风一致，画面连贯"
    target_seconds: int = 30
    round_seconds: int = 5
    resolution: str = Field(default=CONFIG["defaults"]["resolution"])
    seed: int = Field(default=CONFIG["defaults"]["seed"])
    watermark: bool = Field(default=CONFIG["defaults"]["watermark"])
    generate_audio: bool = Field(default=CONFIG["defaults"]["generate_audio"])


def _resolve_media_url(url: str) -> str:
    """把本地上传的 /api/uploads/xxx 转成 base64 data URL（供方舟访问）。"""
    if url.startswith("/api/uploads/"):
        fn = url[len("/api/uploads/"):]
        p = _upload_path(fn)
        if p:
            b64 = base64.b64encode(p.read_bytes()).decode()
            mime = "image/png" if p.suffix == ".png" else ("image/webp" if p.suffix == ".webp" else "image/jpeg")
            return f"data:{mime};base64,{b64}"
    return url


def _resolve_image(src: str) -> tuple[str, Path | None]:
    """把图片来源解析为可提交的 data url + 缩略图路径。支持 data URL、公网 http(s) URL、本地上传 URL。"""
    thumb = None
    if src.startswith("data:image/"):
        data_url = src
        thumb = _save_data_image(src)
    else:
        data_url = _resolve_media_url(src)
        if data_url.startswith("data:image/"):
            thumb = _save_data_image(data_url)
    return data_url, thumb


def _save_data_image(data_url: str) -> Path | None:
    """把 data:image/xxx;base64,... 存成文件，返回路径；失败返回 None。"""
    try:
        if not data_url.startswith("data:image/"):
            return None
        head, _, b64 = data_url.partition(";base64,")
        if not b64:
            return None
        mime = head[len("data:"):]
        ext = "." + mime.split("/")[-1].lower()
        if ext not in ALLOWED_IMAGE_EXT:
            ext = ".png"
        data = base64.b64decode(b64)
        if len(data) > 10 * 1024 * 1024:
            return None
        filename = f"{os.urandom(8).hex()}{ext}"
        path = UP_REF_DIR / filename
        path.write_bytes(data)
        return path
    except Exception:
        return None


def _video_path(name: str) -> Path | None:
    for base in (VIDEO_DIR, V_AI_DIR, V_CUT_DIR, VIDEO_DIR / "ai", VIDEO_DIR / "cut"):
        p = base / name
        if p.exists():
            return p
    return None


def _upload_path(name: str) -> Path | None:
    p = UPLOAD_DIR / name
    if p.exists():
        return p
    for base in (UP_IMG_DIR, UP_FRAME_DIR, UP_REF_DIR, UPLOAD_DIR / "images", UPLOAD_DIR / "frames", UPLOAD_DIR / "refs"):
        q = base / Path(name).name
        if q.exists():
            return q
    return None


async def _download_video(task_id: str, url: str) -> str | None:
    try:
        dest = V_AI_DIR / f"{task_id}.mp4"
        if dest.exists():
            return str(dest)
        await ark_client.download(url, str(dest))
        return str(dest)
    except Exception:
        return None


async def _sync_task(task_id: str) -> dict:
    task = store.get(task_id)
    if not task or task.get("status") in TERMINAL_STATUS:
        return task

    try:
        info = await ark_client.query_task(task_id)
    except Exception as exc:
        store.update(task_id, last_error=f"查询失败: {exc}", updated_at=int(time.time()))
        return store.get(task_id)

    status = info.get("status", task.get("status"))
    update = {
        "status": status,
        "model": info.get("model", task.get("model")),
        "updated_at": int(time.time()),
    }
    if info.get("duration") is not None:
        update["duration"] = info["duration"]

    if "error" in info and info["error"]:
        update["error"] = info["error"]
    content = info.get("content") or {}
    if content.get("video_url"):
        local = await _download_video(task_id, content["video_url"])
        update["video_url"] = content["video_url"]
        update["local_video"] = local
        if content.get("last_frame_url"):
            update["last_frame_url"] = content["last_frame_url"]
    if "usage" in info:
        update["usage"] = info["usage"]

    store.update(task_id, **update)
    return store.get(task_id)


async def _poller():
    while True:
        try:
            for task in store.list():
                if task.get("status") in ACTIVE_STATUS:
                    await _sync_task(task["id"])
        except Exception:
            pass
        await asyncio.sleep(POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for d in (V_AI_DIR, V_CUT_DIR, UP_IMG_DIR, UP_FRAME_DIR, UP_REF_DIR):
        os.makedirs(d, exist_ok=True)
    if not CONFIG["api_key"]:
        print("WARNING: config.json 中未配置 api_key")
    # 启动时清理：上次运行时残留的批量任务（处理器已随进程退出而死亡）
    for job in chain_store.list():
        if job["status"] in ("queued", "running", "cancelling"):
            chain_store.update(job["id"], status="interrupted", stop=True)
    for job in extend_store.list():
        if job["status"] in ("queued", "running", "cancelling"):
            extend_store.update(job["id"], status="interrupted", stop=True)
    for job in image_job_store.list():
        if job["status"] in ("queued", "running", "cancelling"):
            image_job_store.update(job["id"], status="interrupted", stop=True)
    poller = asyncio.create_task(_poller())
    yield
    poller.cancel()


app = FastAPI(title="视频生成工作台", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.middleware("http")
async def no_cache(request, call_next):
    """页面和静态资源禁用缓存，改动后刷新即生效。"""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/config")
async def get_config():
    return {
        "configured": bool(CONFIG["api_key"]),
        "public_base_url": CONFIG.get("public_base_url", ""),
        "has_aks": bool(CONFIG.get("access_key_id") and CONFIG.get("secret_access_key")),
        "default_model": CONFIG["default_model"],
        "models": CONFIG["models"],
        "model_caps": CONFIG["model_caps"],
        "story_model": CONFIG.get("story_model", ""),
        "story_models": CONFIG.get("story_models", {}),
        "image_model": CONFIG.get("image_model", ""),
        "image_models": CONFIG.get("image_models", {}),
        "defaults": CONFIG["defaults"],
    }


@app.get("/api/usage")
async def get_usage(days: int = 7):
    ak = CONFIG.get("access_key_id", "")
    sk = CONFIG.get("secret_access_key", "")
    if not ak or not sk:
        raise HTTPException(400, "未配置 access_key_id / secret_access_key，请在 config.json 填写火山引擎 AK/SK")
    today = time.strftime("%Y-%m-%d")
    start = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
    try:
        rows = await volc_usage.get_usage(ak, sk, start, today, CONFIG.get("usage_apikey_id", ""))
    except Exception as exc:
        raise HTTPException(502, f"查询用量失败: {exc}")
    return {"start": start, "end": today, "rows": rows}


@app.get("/api/balance")
async def get_balance():
    ak = CONFIG.get("access_key_id", "")
    sk = CONFIG.get("secret_access_key", "")
    if not ak or not sk:
        raise HTTPException(400, "未配置 access_key_id / secret_access_key，请在 config.json 填写火山引擎 AK/SK")
    try:
        bal = await volc_usage.get_balance(ak, sk)
    except Exception as exc:
        raise HTTPException(502, f"查询余额失败: {exc}")
    return bal


@app.post("/api/tasks")
async def create_task(req: CreateTaskRequest):
    if not CONFIG["api_key"]:
        raise HTTPException(500, "config.json 中未配置 api_key，请先在 video-studio/config.json 中填写")

    if not req.content:
        raise HTTPException(400, "content 不能为空，请至少填写提示词或上传素材")

    content: list[dict] = []
    thumb_path = None
    prompt_text = ""
    media_count = 0
    for item in req.content:
        if item.type not in VALID_TYPES:
            raise HTTPException(400, f"不支持的素材类型: {item.type}")
        if item.type == "text":
            if not item.text:
                continue
            prompt_text = item.text
            content.append({"type": "text", "text": item.text})
            continue

        if item.type == "image_url":
            url = (item.image_url or {}).get("url")
            if not url:
                raise HTTPException(400, "图片素材缺少 url")
            url = _resolve_media_url(url)
            if item.role and item.role not in {"first_frame", "last_frame", "reference_image"}:
                raise HTTPException(400, f"图片 role 非法: {item.role}")
            if url.startswith("data:image/"):
                saved = _save_data_image(url)
                if saved is not None and thumb_path is None:
                    thumb_path = saved
            content.append(
                {"type": "image_url", "image_url": {"url": url}, "role": item.role or "first_frame"}
            )
        elif item.type == "video_url":
            url = (item.video_url or {}).get("url")
            if not url:
                raise HTTPException(400, "参考视频缺少 url（需公网可访问的 URL）")
            if url.startswith("local://"):
                filename = url[len("local://"):]
                if not CONFIG["public_base_url"]:
                    raise HTTPException(
                        400,
                        "参考视频是本地上传文件，但未配置 public_base_url（公网隧道地址）。"
                        "请先在 config.json 配置，或改用公网 URL。",
                    )
                url = CONFIG["public_base_url"].rstrip("/") + "/api/uploads/" + filename
            content.append({"type": "video_url", "video_url": {"url": url}, "role": "reference_video"})
        elif item.type == "audio_url":
            url = (item.audio_url or {}).get("url")
            if not url:
                raise HTTPException(400, "参考音频缺少 url")
            content.append({"type": "audio_url", "audio_url": {"url": url}, "role": "reference_audio"})
        media_count += 1

    if not content:
        raise HTTPException(400, "没有可提交的内容")

    has_text = any(c["type"] == "text" for c in content)
    has_media = any(c["type"] != "text" for c in content)
    if not has_text and not has_media:
        raise HTTPException(400, "请至少提供提示词或素材")

    payload = {
        "model": req.model,
        "content": content,
        "resolution": req.resolution,
        "ratio": req.ratio,
        "duration": req.duration,
        "seed": req.seed,
        "camera_fixed": req.camera_fixed,
        "watermark": req.watermark,
        "generate_audio": req.generate_audio,
        "omni_reference_task_type": req.omni_reference_task_type,
    }

    try:
        resp = await ark_client.create_task(payload)
    except Exception as exc:
        print(f"[create_task 失败] {req.model} :: {exc}", flush=True)
        if thumb_path is not None and thumb_path.exists():
            os.remove(thumb_path)
        raise HTTPException(502, f"创建任务失败: {exc}")

    task_id = resp["id"]
    _log_prompt("video", req.model, prompt_text or json.dumps(content, ensure_ascii=False)[:4000], task_id)
    task = {
        "id": task_id,
        "model": req.model,
        "prompt": prompt_text,
        "resolution": req.resolution,
        "ratio": req.ratio,
        "duration": req.duration,
        "camera_fixed": req.camera_fixed,
        "watermark": req.watermark,
        "generate_audio": req.generate_audio,
        "task_type": req.omni_reference_task_type,
        "media_count": media_count,
        "image_path": str(thumb_path) if thumb_path else None,
        "status": "queued",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    store.add(task)
    return public_task(task)


async def _process_chain(job_id: str):
    job = chain_store.get(job_id)
    if not job:
        return
    chain_store.update(job_id, status="running")
    prev_last = None
    use_chain = job.get("chain", True)
    for i, item in enumerate(job["items"]):
        if chain_store.get(job_id).get("stop"):
            chain_store.update(job_id, status="cancelled")
            return
        chain_store.update(job_id, current_index=i)
        try:
            first_src, thumb = _resolve_image(item["image"])
        except Exception as exc:
            chain_store.update_item(job_id, i, status="failed", error=str(exc))
            chain_store.update(job_id, status="error", error=f"第{i+1}条素材无效: {exc}")
            return

        content = [{"type": "text", "text": item.get("prompt", "")}]
        if prev_last and use_chain:
            # 首尾帧衔接：上一段尾帧作首帧 + 当前图作尾帧（首帧/尾帧可组合，不能与参考图混用）
            content.append({"type": "image_url", "image_url": {"url": prev_last}, "role": "first_frame"})
            content.append({"type": "image_url", "image_url": {"url": first_src}, "role": "last_frame"})
        else:
            content.append({"type": "image_url", "image_url": {"url": first_src}, "role": "first_frame"})

        item_dur = item.get("duration")
        dur = item_dur if (item_dur is not None and item_dur >= 0) else job["duration"]

        payload = {
            "model": job["model"],
            "content": content,
            "resolution": job["resolution"],
            "ratio": job["ratio"],
            "duration": dur,
            "seed": job.get("seed", -1),
            "camera_fixed": job["camera_fixed"],
            "watermark": job["watermark"],
            "generate_audio": job["generate_audio"],
            "omni_reference_task_type": "auto",
            "return_last_frame": use_chain,
        }
        try:
            resp = await ark_client.create_task(payload)
            task_id = resp["id"]
        except Exception as exc:
            # 回退：若首尾帧不被当前模型支持，退化为「当前图作首帧」
            if prev_last and use_chain:
                fallback_content = [
                    {"type": "text", "text": item.get("prompt", "")},
                    {"type": "image_url", "image_url": {"url": first_src}, "role": "first_frame"},
                ]
                payload["content"] = fallback_content
                try:
                    resp = await ark_client.create_task(payload)
                    task_id = resp["id"]
                except Exception as exc2:
                    chain_store.update_item(job_id, i, status="failed", error=str(exc2)[:300])
                    chain_store.update(job_id, status="error", error=f"第{i+1}条创建失败: {exc2}")
                    return
            else:
                chain_store.update_item(job_id, i, status="failed", error=str(exc)[:300])
                chain_store.update(job_id, status="error", error=f"第{i+1}条创建失败: {exc}")
                return

        chain_store.update_item(job_id, i, task_id=task_id, status="queued")
        store.add({
            "id": task_id,
            "model": job["model"],
            "prompt": item.get("prompt", ""),
            "resolution": job["resolution"],
            "ratio": job["ratio"],
            "duration": dur,
            "seed": job.get("seed", -1),
            "camera_fixed": job["camera_fixed"],
            "watermark": job["watermark"],
            "generate_audio": job["generate_audio"],
            "task_type": "auto",
            "media_count": len(content),
            "image_path": str(thumb) if thumb else None,
            "status": "queued",
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        })

        status = "queued"
        info = {}
        while True:
            if chain_store.get(job_id).get("stop"):
                chain_store.update(job_id, status="cancelled")
                return
            try:
                info = await ark_client.query_task(task_id)
                status = info.get("status", status)
            except Exception:
                pass
            if status in TERMINAL_STATUS:
                break
            await asyncio.sleep(8)

        chain_store.update_item(job_id, i, status=status)
        if status == "succeeded":
            lf = (info.get("content") or {}).get("last_frame_url")
            if lf:
                prev_last = lf
                chain_store.update_item(job_id, i, last_frame_url=lf)
            else:
                prev_last = None
        else:
            err = (info.get("error") or {}).get("message", "")
            chain_store.update_item(job_id, i, error=err[:300])
            prev_last = None

    chain_store.update(job_id, status="done", current_index=len(job["items"]))


@app.get("/api/single_prompts")
async def get_single_prompts():
    p = ROOT / "single_prompts.json"
    if not p.exists():
        return {"items": []}
    data = json.loads(p.read_text(encoding="utf-8"))
    items = [{"name": k, "prompt": v} for k, v in data.items() if not k.startswith("_")]
    return {"items": items}


@app.get("/api/story_prompts")
async def get_story_prompts():
    p = ROOT / "story_prompts.json"
    if not p.exists():
        return {"items": []}
    story = json.loads(p.read_text(encoding="utf-8"))
    items = [{"filename": k, "prompt": v} for k, v in story.items() if not k.startswith("_")]
    items.sort(key=lambda x: int(x["filename"].split(".")[0]))
    return {"items": items}


@app.get("/api/models")
async def list_models():
    if not CONFIG["api_key"]:
        raise HTTPException(400, "未配置 api_key")
    try:
        ids = await ark_client.list_models()
    except Exception as exc:
        raise HTTPException(502, f"获取模型列表失败: {exc}")
    non_chat = ("seedance", "seedream", "seed3d", "seededit", "embedding",
                "hitem3d", "hyper3d", "wan", "smart-router")
    chat = [i for i in ids if not any(m in i for m in non_chat)]
    return {"models": chat}


async def _process_images(job_id: str):
    job = image_job_store.get(job_id)
    if not job:
        return
    try:
        image_job_store.update(job_id, status="running")
        results = []
        total = len(job["prompts"])
        for i, p in enumerate(job["prompts"]):
            if image_job_store.get(job_id).get("stop"):
                image_job_store.update(job_id, status="cancelled")
                return
            image_job_store.update(job_id, current=i + 1, total=total)
            try:
                infos = await ark_client.gen_image(
                    job["model"], p, job["size"], job.get("watermark", False),
                    image=(job.get("references") or None), sequential=job.get("sequential", False),
                )
                for info in infos:
                    b64 = info.get("b64_json")
                    if not b64:
                        continue
                    of = (info.get("output_format") or "").lower()
                    ext = {".jpeg": ".jpg", "jpeg": ".jpg", "jpg": ".jpg", "png": ".png", "webp": ".webp"}.get(of, ".png")
                    if of.startswith("."):
                        ext = of
                    filename = f"{os.urandom(8).hex()}{ext}"
                    (UP_IMG_DIR / filename).write_bytes(base64.b64decode(b64))
                    results.append({"filename": f"gen_images/{filename}", "prompt": p})
            except Exception as exc:
                image_job_store.update(job_id, error=(job.get("error") or "") + f" 第{i+1}张失败: {str(exc)[:200]}")
        image_job_store.update(job_id, status="done", current=total, total=total, results=results)
    except Exception as exc:
        image_job_store.update(job_id, status="error", error=str(exc)[:300])


@app.post("/api/genjob")
async def create_image_job(req: ImageJobRequest):
    if not CONFIG["api_key"]:
        raise HTTPException(500, "config.json 中未配置 api_key")
    if req.model not in CONFIG.get("image_models", {}):
        raise HTTPException(400, f"{req.model} 不是已配置的图片生成模型")
    if not req.prompts:
        raise HTTPException(400, "没有可生成的提示词")
    # 自动清理卡死任务：排队/运行超过 3 分钟的旧任务标记为中断，避免挡住新提交
    now = int(time.time())
    for j in image_job_store.list():
        if j["status"] in ("queued", "running", "cancelling") and now - j.get("created_at", 0) > 180:
            image_job_store.update(j["id"], status="interrupted", stop=True, error="已自动中断（任务卡死超过3分钟）")
    running = [j for j in image_job_store.list() if j["status"] in ("queued", "running", "cancelling")]
    if running:
        raise HTTPException(400, f"已有图片任务在运行（{running[0]['id']}），请先等待或删除")
    job = {
        "id": f"img-{int(time.time())}-{os.urandom(3).hex()}",
        "status": "queued",
        "stop": False,
        "kind": "gen",
        "model": req.model,
        "prompts": req.prompts,
        "size": req.size,
        "watermark": req.watermark,
        "references": req.references,
        "sequential": req.sequential,
        "current": 0,
        "total": len(req.prompts),
        "results": [],
        "created_at": int(time.time()),
    }
    image_job_store.add(job)
    _log_prompt("image", req.model, "\n---\n".join(req.prompts), job["id"])
    asyncio.create_task(_process_images(job["id"]))
    return job


@app.get("/api/genjobs")
async def list_image_jobs():
    return image_job_store.list()


@app.post("/api/genjobs/{job_id}/stop")
async def stop_image_job(job_id: str):
    job = image_job_store.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    if job["status"] in ("done", "cancelled", "error"):
        return {"ok": True, "already": job["status"]}
    image_job_store.update(job_id, stop=True, status="cancelling")
    return {"ok": True}


@app.delete("/api/genjobs/{job_id}")
async def delete_image_job(job_id: str):
    job = image_job_store.get(job_id)
    if job:
        for r in job.get("results", []):
            p = _upload_path(r["filename"])
            if p:
                try:
                    os.remove(p)
                except OSError:
                    pass
    image_job_store.delete(job_id)
    return {"ok": True}


@app.post("/api/storyboard")
async def storyboard(req: StoryboardRequest):
    if not CONFIG["api_key"]:
        raise HTTPException(500, "config.json 中未配置 api_key")
    model = req.model or CONFIG.get("story_model", "")
    if not model:
        raise HTTPException(400, "未配置分镜用的对话模型。请在 config.json 的 story_models 里配置一个你已开通的对话模型，再重试")
    if not req.story.strip():
        raise HTTPException(400, "故事内容为空")
    n = max(1, req.count)
    system = (
        "你是短视频分镜脚本生成器。用户提供一段完整故事，需要按情节顺序切成 "
        f"恰好 {n} 个镜头，每个镜头对应一个画面。"
        "请为每个镜头写一段镜头描述（1-3 句话，中文），描述该镜头画面内容、人物动作、镜头运动、氛围。"
        f"严格只输出 {n} 行，每行格式：数字加句点加空格加描述，例如：\n1. ……\n2. ……\n不要输出任何其他内容。"
    )
    user = f"故事：\n{req.story}\n\n请切成 {n} 个镜头描述。"
    try:
        content = await ark_client.chat(model, f"{system}\n\n{user}")
    except Exception as exc:
        raise HTTPException(502, f"AI 分镜失败: {exc}")

    parts = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        # 去掉 "1. " / "1、" / "- " 等前缀
        stripped = line
        import re
        m = re.match(r"^[-\d\s]*[.、\)]?\s*(.*)$", line)
        if m and m.group(1).strip():
            stripped = m.group(1).strip()
        parts.append(stripped)
        if len(parts) >= n:
            break
    return {"items": parts}


@app.post("/api/chain")
async def create_chain(req: CreateChainRequest):
    if not CONFIG["api_key"]:
        raise HTTPException(500, "config.json 中未配置 api_key")
    if not req.items:
        raise HTTPException(400, "请至少添加一个素材")
    for it in req.items:
        if not it.prompt and not it.image:
            raise HTTPException(400, "素材缺少提示词或图片")

    running = [j for j in chain_store.list() if j["status"] in ("queued", "running", "cancelling")]
    if running:
        raise HTTPException(400, f"已有批量任务正在运行（{running[0]['id']}），请先等待完成或停止它，避免重复生成")

    job = {
        "id": f"job-{int(time.time())}-{os.urandom(3).hex()}",
        "status": "queued",
        "stop": False,
        "chain": req.chain,
        "model": req.model,
        "resolution": req.resolution,
        "ratio": req.ratio,
        "duration": req.duration,
        "seed": req.seed,
        "camera_fixed": req.camera_fixed,
        "watermark": req.watermark,
        "generate_audio": req.generate_audio,
        "current_index": 0,
        "total": len(req.items),
        "created_at": int(time.time()),
        "items": [
            {"prompt": it.prompt, "image": it.image, "duration": it.duration, "status": "pending", "task_id": None, "error": None}
            for it in req.items
        ],
    }
    chain_store.add(job)
    _log_prompt("chain", req.model, "\n---\n".join(it.prompt for it in req.items), job["id"])
    asyncio.create_task(_process_chain(job["id"]))
    return job


@app.get("/api/chain")
async def list_chain():
    return chain_store.list()


@app.delete("/api/chain/{job_id}")
async def delete_chain(job_id: str):
    chain_store.delete(job_id)
    return {"ok": True}


async def _process_extend(job_id: str):
    job = extend_store.get(job_id)
    if not job:
        return
    extend_store.update(job_id, status="running")
    cur_video = job["video_url"]
    total = 0.0
    rounds = job.get("rounds", [])
    for i in range(job["max_rounds"]):
        if extend_store.get(job_id).get("stop"):
            extend_store.update(job_id, status="cancelled")
            return
        if total >= job["target_seconds"]:
            break
        remaining = job["target_seconds"] - total
        chunk = min(job["round_seconds"], remaining)
        prompt = f"{job['prompt']}，向后延长 {int(chunk)} 秒"
        content = [
            {"type": "text", "text": prompt},
            {"type": "video_url", "video_url": {"url": cur_video}, "role": "reference_video"},
        ]
        payload = {
            "model": job["model"],
            "content": content,
            "resolution": job["resolution"],
            "ratio": "adaptive",
            "duration": -1,
            "seed": job.get("seed", -1),
            "watermark": job.get("watermark", False),
            "generate_audio": job.get("generate_audio", True),
            "omni_reference_task_type": "extend",
        }
        try:
            resp = await ark_client.create_task(payload)
            task_id = resp["id"]
        except Exception as exc:
            extend_store.update(job_id, status="error", error=f"第{i+1}轮延长创建失败: {exc}")
            return
        extend_store.update(job_id, current_round=i + 1)
        store.add({
            "id": task_id,
            "model": job["model"],
            "prompt": prompt,
            "resolution": job["resolution"],
            "ratio": "adaptive",
            "duration": -1,
            "seed": job.get("seed", -1),
            "camera_fixed": False,
            "watermark": job.get("watermark", False),
            "generate_audio": job.get("generate_audio", True),
            "task_type": "extend",
            "media_count": 1,
            "image_path": None,
            "status": "queued",
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        })
        status = "queued"
        info = {}
        while True:
            if extend_store.get(job_id).get("stop"):
                extend_store.update(job_id, status="cancelled")
                return
            try:
                info = await ark_client.query_task(task_id)
                status = info.get("status", status)
            except Exception:
                pass
            if status in TERMINAL_STATUS:
                break
            await asyncio.sleep(8)
        if status == "succeeded":
            new_video = (info.get("content") or {}).get("video_url")
            if not new_video:
                break
            dur = float(info.get("duration") or chunk)
            total += dur
            cur_video = new_video
            rounds.append({"round": i + 1, "task_id": task_id, "status": "succeeded", "duration": dur, "video_url": new_video})
            extend_store.update(job_id, rounds=rounds, total_duration=int(total))
        else:
            rounds.append({"round": i + 1, "task_id": task_id, "status": status,
                           "error": (info.get("error") or {}).get("message", "")[:300]})
            extend_store.update(job_id, rounds=rounds, total_duration=int(total))
            break
    extend_store.update(job_id, status="done", current_round=len(rounds), total_duration=int(total), final_video=cur_video)


@app.post("/api/extendjob")
async def create_extend_job(req: ExtendJobRequest):
    if not CONFIG["api_key"]:
        raise HTTPException(500, "config.json 中未配置 api_key")
    caps = CONFIG["model_caps"].get(req.model, {})
    task_types = caps.get("task_types", [])
    if "extend" not in task_types:
        raise HTTPException(400, f"模型 {req.model} 不支持视频延长（需 2.0/2.5）")
    video = req.video_url
    if video.startswith("local://"):
        fn = video[len("local://"):]
        if not CONFIG["public_base_url"]:
            raise HTTPException(400, "本地上传视频需要配置 public_base_url（公网隧道）")
        video = CONFIG["public_base_url"].rstrip("/") + "/api/uploads/" + fn
    if not (video.startswith("http://") or video.startswith("https://")):
        raise HTTPException(400, "参考视频需要公网 http(s) URL")
    if req.target_seconds < 10 or req.target_seconds > 600:
        raise HTTPException(400, "目标总时长需在 10~600 秒之间")
    max_rounds = min(30, max(1, int(req.target_seconds / max(1, req.round_seconds)) + 1))
    running = [j for j in extend_store.list() if j["status"] in ("queued", "running", "cancelling")]
    if running:
        raise HTTPException(400, f"已有延长任务在运行（{running[0]['id']}），请先等待或停止")
    job = {
        "id": f"ext-{int(time.time())}-{os.urandom(3).hex()}",
        "status": "queued",
        "stop": False,
        "model": req.model,
        "video_url": video,
        "prompt": req.prompt,
        "target_seconds": req.target_seconds,
        "round_seconds": req.round_seconds,
        "max_rounds": max_rounds,
        "resolution": req.resolution,
        "seed": req.seed,
        "watermark": req.watermark,
        "generate_audio": req.generate_audio,
        "current_round": 0,
        "total_duration": 0,
        "rounds": [],
        "created_at": int(time.time()),
    }
    extend_store.add(job)
    _log_prompt("extend", req.model, f"{req.prompt}（参考视频: {req.video_url}）", job["id"])
    asyncio.create_task(_process_extend(job["id"]))
    return job


@app.get("/api/extendjobs")
async def list_extend_jobs():
    return extend_store.list()


@app.post("/api/extendjobs/{job_id}/stop")
async def stop_extend_job(job_id: str):
    job = extend_store.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    if job["status"] in ("done", "cancelled", "error"):
        return {"ok": True, "already": job["status"]}
    extend_store.update(job_id, stop=True, status="cancelling")
    return {"ok": True}


@app.delete("/api/extendjobs/{job_id}")
async def delete_extend_job(job_id: str):
    extend_store.delete(job_id)
    return {"ok": True}


@app.post("/api/chain/{job_id}/stop")
async def stop_chain(job_id: str):
    job = chain_store.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    if job["status"] in ("done", "cancelled", "error"):
        return {"ok": True, "already": job["status"]}
    chain_store.update(job_id, stop=True, status="cancelling")
    return {"ok": True}


@app.get("/api/tasks")
async def list_tasks():
    return [public_task(t) for t in store.list()]


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    task = await _sync_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return public_task(task)


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    task = store.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    store.delete(task_id)
    for key in ("image_path", "local_video"):
        p = task.get(key)
        if p and Path(p).exists():
            try:
                os.remove(p)
            except OSError:
                pass
    return {"ok": True}


class MoveRequest(BaseModel):
    videos: list[str] = []
    files: list[str] = []
    dest: str = ""


@app.get("/api/move-roots")
async def move_roots():
    subdirs = []
    if MOVE_ROOT.is_dir():
        for d in sorted(MOVE_ROOT.iterdir()):
            if d.is_dir():
                subdirs.append(str(d.relative_to(MOVE_ROOT)))
    return {
        "root": str(MOVE_ROOT),
        "base": str(MOVE_BASE),
        "root_exists": MOVE_ROOT.is_dir(),
        "subdirs": subdirs,
    }


@app.post("/api/move")
async def move_resources(req: MoveRequest):
    try:
        if req.dest and Path(req.dest).is_absolute():
            dest_dir = Path(req.dest).resolve()
        else:
            dest_dir = (MOVE_ROOT / req.dest).resolve()
        base = MOVE_BASE.resolve()
        if dest_dir != base and base not in dest_dir.parents:
            raise HTTPException(400, f"目标目录必须在 {base} 之内")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "目标目录无效")
    dest_dir.mkdir(parents=True, exist_ok=True)

    moved, errors = [], []
    for task_id in req.videos:
        src = _video_path(f"{task_id}.mp4")
        if not src:
            errors.append(f"视频 {task_id} 不存在")
            continue
        try:
            dst = dest_dir / src.name
            shutil.move(str(src), str(dst))
            store.update(task_id, moved_to=str(dst), local_video=None)
            moved.append({"kind": "video", "name": src.name, "dest": str(dst)})
        except Exception as exc:
            errors.append(f"{task_id} 移动失败: {exc}")
    for fn in req.files:
        src = _upload_path(fn)
        if not src:
            errors.append(f"文件 {fn} 不存在")
            continue
        try:
            dst = dest_dir / src.name
            shutil.move(str(src), str(dst))
            moved.append({"kind": "file", "name": src.name, "dest": str(dst)})
        except Exception as exc:
            errors.append(f"{fn} 移动失败: {exc}")
    return {"moved": moved, "errors": errors}


class RemoveSrcRequest(BaseModel):
    kind: str
    name: str
    dest_name: str = ""


@app.post("/api/remove-src")
async def remove_src(req: RemoveSrcRequest):
    if req.kind == "video":
        src = _video_path(f"{req.name}.mp4")
        if src:
            src.unlink()
        store.update(req.name, moved_to=f"已移出（{req.dest_name or '文件管理器'}）", local_video=None)
        return {"ok": True}
    if req.kind == "file":
        src = _upload_path(req.name)
        if src:
            src.unlink()
        for job in image_job_store.list():
            results = job.get("results", [])
            if any(r["filename"] == req.name for r in results):
                image_job_store.update(job["id"], results=[r for r in results if r["filename"] != req.name])
        return {"ok": True}
    raise HTTPException(400, "kind 无效")


@app.get("/api/fs/browse")
async def fs_browse(path: str = ""):
    try:
        cur = Path(path).resolve() if path else MOVE_ROOT.resolve()
        base = MOVE_BASE.resolve()
        if cur != base and base not in cur.parents:
            raise HTTPException(400, "只能浏览 ai-learning 目录内")
        if not cur.is_dir():
            raise HTTPException(400, "不是目录")
        subdirs = sorted([d.name for d in cur.iterdir() if d.is_dir()])
        parent = str(cur.parent) if (cur != base and base in cur.parents) else ""
        return {"path": str(cur), "parent": parent, "subdirs": subdirs, "name": cur.name}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"无法浏览: {exc}")


class CutRequest(BaseModel):
    task_id: str
    mode: str = "start"
    seconds: int = 5


def _video_duration(path: str) -> float | None:
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, timeout=60,
        )
        if res.returncode != 0:
            return None
        return float(res.stdout.strip())
    except Exception:
        return None


@app.post("/api/cut")
async def cut_video(req: CutRequest):
    task = store.get(req.task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    src = _video_path(f"{req.task_id}.mp4")
    if not src:
        raise HTTPException(400, "本地视频不存在，无法截取")
    if req.mode not in ("start", "end"):
        raise HTTPException(400, "mode 无效")
    if not (1 <= req.seconds <= 300):
        raise HTTPException(400, "截取时长需在 1-300 秒之间")
    dur = _video_duration(str(src))
    if dur is None:
        raise HTTPException(500, "无法读取视频时长")
    if req.mode == "end":
        if req.seconds >= dur:
            raise HTTPException(400, f"截取结尾 {req.seconds}s 超过视频总长 {dur:.1f}s")
        start = max(0.0, dur - req.seconds)
    else:
        if req.seconds > dur:
            raise HTTPException(400, f"截取开头 {req.seconds}s 超过视频总长 {dur:.1f}s")
        start = 0.0
    out_id = f"cut-{int(time.time())}-{os.urandom(3).hex()}"
    out = V_CUT_DIR / f"{out_id}.mp4"
    cmd = [
        "ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(src),
        "-t", str(req.seconds), "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", str(out),
    ]
    try:
        res = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, timeout=900)
    except subprocess.TimeoutExpired:
        raise HTTPException(500, "ffmpeg 超时")
    if res.returncode != 0:
        raise HTTPException(500, f"ffmpeg 失败: {(res.stderr or b'').decode('utf-8', 'ignore')[-300:]}")
    new_task = {
        "id": out_id,
        "status": "done",
        "model": task.get("model", ""),
        "prompt": f"✂ 截取{('开头' if req.mode == 'start' else '结尾')} {req.seconds} 秒（源 {req.task_id}）",
        "resolution": task.get("resolution", ""),
        "local_video": str(out),
        "duration": req.seconds,
        "created_at": int(time.time()),
    }
    store.add(new_task)
    return new_task


class FramesRequest(BaseModel):
    task_id: str
    count: int = 8
    mode: str = "start"
    range: str = ""


def _video_frames(path: str) -> int | None:
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
             "-show_entries", "stream=nb_read_frames", "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, timeout=120,
        )
        if res.returncode != 0:
            return None
        return int(float(res.stdout.strip()))
    except Exception:
        return None


@app.post("/api/frames")
async def extract_frames(req: FramesRequest):
    task = store.get(req.task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    src = _video_path(f"{req.task_id}.mp4")
    if not src:
        raise HTTPException(400, "本地视频不存在，无法抽帧")
    if not (1 <= req.count <= 60):
        raise HTTPException(400, "帧数需在 1-60 之间")
    dur = _video_duration(str(src))
    if dur is None or dur <= 0:
        raise HTTPException(500, "无法读取视频时长")
    out_id = f"img-{int(time.time())}-{os.urandom(3).hex()}"
    rng = req.range.strip()
    if rng:
        # 区间模式：如 "2-4" 在 2s~4s 内均匀抽 N 帧
        if "-" not in rng:
            raise HTTPException(400, "区间格式应为 开始-结束，如 2-4")
        try:
            a, b = rng.split("-", 1)
            a, b = float(a), float(b)
        except ValueError:
            raise HTTPException(400, "区间格式应为 开始-结束，如 2-4")
        if a < 0 or b <= a or b > dur:
            raise HTTPException(400, f"区间需满足 0 ≤ 开始 < 结束 ≤ 视频总长 {dur:.1f}s")
        seg = b - a
        fps = req.count / seg
        cmd = ["ffmpeg", "-y", "-ss", f"{a:.3f}", "-i", str(src), "-t", f"{seg:.3f}",
               "-vf", f"fps={fps:.6f}", "-q:v", "2", str(UP_FRAME_DIR / f"{out_id}_%03d.jpg")]
        desc = f"从 {req.task_id} 区间 {a:.0f}-{b:.0f}s 抽 {req.count} 帧"
    else:
        # 位置模式：开头=取前 N 帧；结尾=取最后 N 帧
        if req.mode not in ("start", "end"):
            raise HTTPException(400, "mode 无效")
        total = _video_frames(str(src))
        if total is None or total <= 0:
            raise HTTPException(500, "无法读取视频总帧数")
        if req.count > total:
            raise HTTPException(400, f"帧数 {req.count} 超过视频总帧数 {total}")
        if req.mode == "start":
            select_expr = f"lt(n\\,{req.count})"
        else:
            select_expr = f"gte(n\\,{total - req.count})"
        cmd = ["ffmpeg", "-y", "-i", str(src), "-vf", f"select='{select_expr}'", "-fps_mode", "passthrough",
               "-q:v", "2", str(UP_FRAME_DIR / f"{out_id}_%03d.jpg")]
        desc = f"从 {req.task_id} {('开头' if req.mode == 'start' else '结尾')}取 {req.count} 帧"
    try:
        res = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise HTTPException(500, "ffmpeg 超时")
    if res.returncode != 0:
        raise HTTPException(500, f"ffmpeg 抽帧失败: {(res.stderr or b'').decode('utf-8', 'ignore')[-300:]}")
    files = sorted(UP_FRAME_DIR.glob(f"{out_id}_*.jpg"))
    if not files:
        raise HTTPException(500, "未抽到任何帧")
    results = [{"filename": f"cut_frames/{f.name}", "prompt": f"帧 {i + 1}/{len(files)}（源 {req.task_id}）"} for i, f in enumerate(files)]
    job = {
        "id": out_id, "status": "done", "stop": False, "kind": "frame", "model": task.get("model", ""),
        "prompts": [desc],
        "size": "", "watermark": False, "references": [], "sequential": False,
        "current": len(files), "total": len(files), "results": results, "created_at": int(time.time()),
    }
    image_job_store.add(job)
    return job


@app.get("/api/uploads/{filename:path}")
async def upload_file(filename: str):
    path = _upload_path(filename)
    if not path:
        raise HTTPException(404, "文件不存在")
    return FileResponse(str(path))


@app.post("/api/upload")
async def upload_file_post(file: UploadFile = File(...)):
    if file.content_type not in {"video/mp4", "video/quicktime", "application/octet-stream"}:
        raise HTTPException(400, "仅支持 mp4 / mov 视频")
    data = await file.read()
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(400, "视频不能超过 50MB")
    filename = f"{os.urandom(8).hex()}.mp4"
    (UP_REF_DIR / filename).write_bytes(data)
    return {"filename": f"refs/{filename}"}


@app.post("/api/upload_image")
async def upload_image_post(file: UploadFile = File(...)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(400, "仅支持 jpg/png/webp 图片")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(400, "图片不能超过 10MB")
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(file.content_type, ".png")
    filename = f"{os.urandom(8).hex()}{ext}"
    (UP_REF_DIR / filename).write_bytes(data)
    return {"filename": f"refs/{filename}"}


@app.get("/api/videos/{filename:path}")
async def video_file(filename: str):
    path = _video_path(Path(filename).name)
    if not path:
        raise HTTPException(404, "视频不存在")
    return FileResponse(str(path), media_type="video/mp4")