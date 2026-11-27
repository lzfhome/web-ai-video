"""Ark（火山方舟）HTTP 客户端：配置、请求、任务轮询、下载。

只管网络和鉴权，不碰 CLI、不打印计划、不决定文件放哪。
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[3]
VS = Path(os.environ.get("VIDEO_STUDIO_DIR") or AIWORK / "tools/video-studio").expanduser().resolve()

DEFAULT_VIDEO = "doubao-seedance-2-5-flash-261115"
DEFAULT_IMAGE = "doubao-seedream-5-5-261028"

_API_KEY: str | None = None
_BASE: str | None = None


def load_config() -> tuple[str, str]:
    """读 video-studio 的 config.json + config.secrets.json；环境变量优先。"""
    cfg: dict = {}
    for name in ("config.json", "config.secrets.json"):
        p = VS / name
        if p.exists():
            try:
                cfg.update(json.loads(p.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass
    key = os.environ.get("ARK_API_KEY") or cfg.get("api_key")
    base = os.environ.get("ARK_BASE_URL") or cfg.get("base_url") or "https://ark.cn-beijing.volces.com/api/v3"
    if not key:
        sys.exit(f"缺 Ark API Key：在 {VS}/config.secrets.json 配 api_key，或设 ARK_API_KEY")
    return key, base.rstrip("/")


def ensure_config() -> None:
    global _API_KEY, _BASE
    if _API_KEY is None:
        _API_KEY, _BASE = load_config()


def api(method: str, path: str, payload: dict | None = None, timeout: int = 300) -> dict:
    ensure_config()
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        _BASE + path, data=data, method=method,
        headers={"Authorization": f"Bearer {_API_KEY}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:1000]
        sys.exit(f"Ark HTTP {e.code}: {body}")


def data_url(path: Path) -> str:
    ext = path.suffix.lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def download(url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "vibe-knowledge/ark"})
    with urllib.request.urlopen(req, timeout=600) as r, open(out, "wb") as f:
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)


def generate_images(payload: dict) -> list[dict]:
    """POST /images/generations，返回 data[]（每项含 b64_json / output_format）。"""
    data = api("POST", "/images/generations", payload)
    items = data.get("data") or []
    if not items:
        sys.exit(f"图片生成返回异常：{str(data)[:400]}")
    return items


def create_video_task(payload: dict) -> str:
    task = api("POST", "/contents/generations/tasks", payload)
    tid = task.get("id")
    if not tid:
        sys.exit(f"创建任务失败：{str(task)[:400]}")
    return tid


def wait_video_task(tid: str, poll: int = 5, timeout: int = 1800, log=print) -> dict:
    """轮询到 succeeded/failed/expired/cancelled，返回最后一次任务详情。"""
    status, info = "queued", {}
    deadline = time.time() + timeout
    while time.time() < deadline:
        info = api("GET", f"/contents/generations/tasks/{tid}")
        status = str(info.get("status", "")).lower()
        log(f"  {time.strftime('%H:%M:%S')}  {status}")
        if status in ("succeeded", "failed", "expired", "cancelled"):
            break
        time.sleep(max(2, poll))
    if status != "succeeded":
        sys.exit(f"任务未成功：{status} {json.dumps(info, ensure_ascii=False)[:600]}")
    return info


def video_url(info: dict) -> str:
    url = (info.get("content") or {}).get("video_url")
    if not url:
        sys.exit(f"没有 video_url：{json.dumps(info, ensure_ascii=False)[:600]}")
    return url
