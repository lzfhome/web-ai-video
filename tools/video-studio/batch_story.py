#!/usr/bin/env python3
"""批量生成坤坤故事视频：11 张图，每张一个任务。

用法：
    python3 batch_story.py              # 并行提交全部 11 个独立任务（互不衔接）
    python3 batch_story.py --chain      # 串行 + 尾帧衔接（推荐）：上一条的尾帧作为下一条首帧
    python3 batch_story.py --chain --dry-run   # 只打印计划，不实际调用
"""
import argparse
import asyncio
import base64
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KUN_DIR = ROOT.parent / "kun"
STORY_FILE = ROOT / "story_prompts.json"

sys.path.insert(0, str(ROOT))
import ark_client  # noqa: E402
from config import CONFIG  # noqa: E402
from store import TaskStore  # noqa: E402

MODEL = CONFIG["default_model"]
RESOLUTION = CONFIG["defaults"]["resolution"]
RATIO = "adaptive"
DURATION = CONFIG["defaults"]["duration"]
WATERMARK = CONFIG["defaults"]["watermark"]
GENERATE_AUDIO = CONFIG["defaults"]["generate_audio"]

store = TaskStore(str(ROOT / "data" / "tasks.json"))
UPLOAD_DIR = ROOT / "data" / "uploads"
TERMINAL = {"succeeded", "failed", "expired", "cancelled"}


def img_data_url(path: Path) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:image/png;base64,{b64}"


def save_thumb(img: Path) -> str:
    thumb_name = f"{int(time.time())}_{img.stem}.png"
    (UPLOAD_DIR / thumb_name).write_bytes(img.read_bytes())
    return str(UPLOAD_DIR / thumb_name)


def build_payload(prompt: str, content: list[dict], return_last_frame: bool) -> dict:
    return {
        "model": MODEL,
        "content": content,
        "resolution": RESOLUTION,
        "ratio": RATIO,
        "duration": DURATION,
        "camera_fixed": False,
        "watermark": WATERMARK,
        "generate_audio": GENERATE_AUDIO,
        "omni_reference_task_type": "auto",
        "return_last_frame": return_last_frame,
    }


def store_task(task_id: str, prompt: str, thumb: str | None, content_sz: int):
    store.add({
        "id": task_id,
        "model": MODEL,
        "prompt": prompt,
        "resolution": RESOLUTION,
        "ratio": RATIO,
        "duration": DURATION,
        "camera_fixed": False,
        "watermark": WATERMARK,
        "generate_audio": GENERATE_AUDIO,
        "task_type": "auto",
        "media_count": content_sz,
        "image_path": thumb,
        "status": "queued",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    })


def run(coro):
    return asyncio.run(coro)


async def create(payload) -> str:
    resp = await ark_client.create_task(payload)
    return resp["id"]


async def wait_terminal(task_id: str, interval: int = 8) -> dict:
    while True:
        info = await ark_client.query_task(task_id)
        status = info.get("status", "")
        if status in TERMINAL:
            return info
        time.sleep(interval)


def submit_all(entries):
    """并行提交全部独立任务。"""
    created = []
    for filename, prompt in entries:
        img = KUN_DIR / filename
        if not img.exists():
            print(f"[跳过] 图片不存在: {img}")
            continue
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": img_data_url(img)}, "role": "first_frame"},
        ]
        payload = build_payload(prompt, content, return_last_frame=False)
        try:
            task_id = run(create(payload))
        except Exception as exc:
            print(f"[失败] {filename}: {exc}")
            continue
        store_task(task_id, prompt, save_thumb(img), len(content))
        created.append((filename, task_id))
        print(f"[已提交] {filename} -> {task_id}")
    return created


def submit_chain(entries):
    """串行生成，尾帧衔接：上一条的尾帧作为下一条的首帧。"""
    created = []
    prev_last_frame = None
    for idx, (filename, prompt) in enumerate(entries):
        img = KUN_DIR / filename
        if not img.exists():
            print(f"[跳过] 图片不存在: {img}")
            continue

        if idx == 0 or prev_last_frame is None:
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": img_data_url(img)}, "role": "first_frame"},
            ]
        else:
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": prev_last_frame}, "role": "first_frame"},
                {"type": "image_url", "image_url": {"url": img_data_url(img)}, "role": "last_frame"},
            ]
        payload = build_payload(prompt, content, return_last_frame=True)

        print(f"[{idx+1}/{len(entries)}] {filename} 创建任务…")
        try:
            task_id = run(create(payload))
        except Exception as exc:
            print(f"  [失败] 创建 {filename}: {exc}")
            prev_last_frame = None
            continue
        store_task(task_id, prompt, save_thumb(img), len(content))
        created.append((filename, task_id))
        print(f"  任务 {task_id}，等待生成（mini 并发1，约1-2分钟）…")

        info = run(wait_terminal(task_id))
        status = info.get("status")
        print(f"  [{status}] {filename}")

        if status == "succeeded":
            lf = (info.get("content") or {}).get("last_frame_url")
            if lf:
                prev_last_frame = lf
                print(f"  尾帧已获取，将作为下一段首帧")
            else:
                prev_last_frame = None
                print(f"  [提示] 未返回尾帧，下一段将用原图作为首帧")
        else:
            err = (info.get("error") or {}).get("message", "")
            print(f"  [错误] {err[:200]}")
            prev_last_frame = None
    return created


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", action="store_true", help="串行生成 + 尾帧衔接")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不调用 API")
    ap.add_argument("--watch", action="store_true", help="（无 chain 时）提交后持续轮询直到全部完成")
    args = ap.parse_args()

    if not CONFIG["api_key"]:
        sys.exit("config.json 未配置 api_key")

    story = json.loads(STORY_FILE.read_text(encoding="utf-8"))
    entries = [(k, v) for k, v in story.items() if not k.startswith("_")]
    entries.sort(key=lambda kv: int(kv[0].split(".")[0]))

    if args.dry_run:
        print("【计划】" + ("尾帧衔接模式" if args.chain else "独立模式"))
        for i, (fname, prompt) in enumerate(entries, 1):
            extra = "" if (i == 1 or not args.chain) else "（首帧=上一段尾帧 + 参考图=" + fname + "）"
            print(f"  {fname}: {prompt[:40]}… {extra}")
        print(f"共 {len(entries)} 条。")
        return

    if args.chain:
        print("=== 尾帧衔接模式开始（串行，预计 15-25 分钟）===")
        created = submit_chain(entries)
    else:
        print("=== 独立模式：并行提交全部任务 ===")
        created = submit_all(entries)
        if args.watch and created:
            print("\n等待全部完成（Web 界面也会同步显示）…")
            watch(created)

    print(f"\n完成，共 {len(created)} 条。打开 http://localhost:8000 查看。")


def watch(tasks):
    pending = set(tid for _, tid in tasks)
    while pending:
        for _, tid in tasks:
            if tid not in pending:
                continue
            try:
                info = run(ark_client.query_task(tid))
            except Exception:
                continue
            if info.get("status") in TERMINAL:
                pending.discard(tid)
                print(f"[{info.get('status')}] {tid}")
        if pending:
            time.sleep(10)


if __name__ == "__main__":
    main()