#!/usr/bin/env python3
"""BGM 获取（Agent 用）：搜索 / 下载 / 网易云免费版 / 探测 / 建索引。

原则：音频文件只进 resources/music/，不进 cine/。
所有命令输出 JSON，方便 agent 直接解析；错误也输出 JSON 并以非 0 退出。

示例：
  python cine/audio/tools/get_bgm.py search "花火が瞬く夜に 羽肿" --limit 5
  python cine/audio/tools/get_bgm.py download "https://www.youtube.com/watch?v=xZ5Rrrul7h8" \
      --name hanabi_yuzhong --proxy socks5://127.0.0.1:1080
  python cine/audio/tools/get_bgm.py netease 434902428 --name hanabi_yuzhong_128
  python cine/audio/tools/get_bgm.py probe "resources/music/hanabi_yuzhong.mp3"
  python cine/audio/tools/get_bgm.py library
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MUSIC = ROOT / "resources" / "music"
INCOMING = MUSIC / "_incoming"


def _find_tool(name: str, env: str, local_globs: list[str]) -> str | None:
    if os.environ.get(env):
        return os.environ[env]
    found = shutil.which(name)
    if found:
        return found
    for pattern in local_globs:
        hits = sorted(ROOT.glob(pattern))
        if hits:
            return str(hits[-1])
    return None


YTDLP = _find_tool(
    "yt-dlp",
    "YT_DLP",
    ["tools/local/yt-dlp/yt-dlp.exe", "tools/local/yt-dlp/yt-dlp"],
)
FFMPEG = _find_tool(
    "ffmpeg",
    "FFMPEG",
    ["tools/local/ffmpeg/*/bin/ffmpeg.exe", "tools/local/ffmpeg/*/bin/ffmpeg"],
)
FFPROBE = _find_tool(
    "ffprobe",
    "FFPROBE",
    ["tools/local/ffmpeg/*/bin/ffprobe.exe", "tools/local/ffmpeg/*/bin/ffprobe"],
)

# yt-dlp 是 PyInstaller 打包的；强制子进程用 UTF-8，避免 Windows 下中文标题变 \ufffd
SUBPROCESS_ENV = os.environ.copy()
SUBPROCESS_ENV.setdefault("PYTHONIOENCODING", "utf-8")
SUBPROCESS_ENV.setdefault("PYTHONUTF8", "1")


def emit(obj) -> None:
    # ensure_ascii=True：Windows 控制台/工具链不会把中文 JSON 弄乱
    print(json.dumps(obj, ensure_ascii=True, indent=2))


def fail(message: str, **extra) -> "NoReturn":
    emit({"ok": False, "error": message, **extra})
    raise SystemExit(1)


def need_tools(*, need_ffmpeg: bool = True) -> None:
    if not YTDLP:
        fail("找不到 yt-dlp；设置 YT_DLP 或放到 tools/local/yt-dlp/yt-dlp.exe")
    if need_ffmpeg and (not FFMPEG or not FFPROBE):
        fail("找不到 ffmpeg/ffprobe；设置 FFMPEG/FFPROBE 或放到 tools/local/ffmpeg/*/bin/")


def safe_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        fail("--name 只能用 ASCII 字母、数字、点、下划线、连字符")
    return name


def probe(path: Path) -> dict:
    if not FFPROBE:
        fail("找不到 ffprobe")
    p = subprocess.run(
        [
            FFPROBE,
            "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:format_tags=title,artist,album",
            "-show_entries", "stream=codec_name,sample_rate,channels",
            "-of", "json",
            str(path),
        ],
        capture_output=True,
    )
    if p.returncode != 0:
        fail("ffprobe 失败", stderr=p.stderr.decode("utf-8", errors="replace")[-2000:])
    try:
        data = json.loads(p.stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        fail(f"ffprobe JSON 解析失败: {exc}")
    fmt = data.get("format", {})
    stream = (data.get("streams") or [{}])[0]
    tags = fmt.get("tags", {}) or {}
    return {
        "duration": float(fmt["duration"]) if fmt.get("duration") else None,
        "size": int(fmt["size"]) if fmt.get("size") else path.stat().st_size,
        "bit_rate": int(fmt["bit_rate"]) if fmt.get("bit_rate") else None,
        "codec": stream.get("codec_name"),
        "sample_rate": int(stream["sample_rate"]) if stream.get("sample_rate") else None,
        "channels": stream.get("channels"),
        "tags": {
            "title": tags.get("title"),
            "artist": tags.get("artist"),
            "album": tags.get("album"),
        },
    }


def sidecar_for(name: str) -> Path:
    return MUSIC / f"{name}.json"


def write_sidecar(name: str, payload: dict) -> Path:
    path = sidecar_for(name)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def finish_file(name: str, src: Path, meta: dict) -> dict:
    final = MUSIC / f"{name}{src.suffix.lower()}"
    final.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != final.resolve():
        shutil.move(str(src), str(final))
    info = probe(final)
    payload = {
        "file": final.name,
        "path": str(final),
        "title": meta.get("title") or info["tags"].get("title"),
        "artist": meta.get("artist") or info["tags"].get("artist"),
        "album": meta.get("album") or info["tags"].get("album"),
        "source": meta.get("source"),
        "source_url": meta.get("source_url"),
        "source_id": meta.get("source_id"),
        "license": meta.get("license", "unknown"),
        "usage": meta.get("usage", "self-use"),
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "probe": info,
    }
    sidecar = write_sidecar(name, payload)
    return {"ok": True, "file": str(final), "sidecar": str(sidecar), "meta": payload}


def cmd_search(args) -> None:
    need_tools(need_ffmpeg=False)
    cmd = [
        YTDLP,
        "--no-warnings",
        "--flat-playlist",
        "--print",
        "%(id)s\t%(duration)s\t%(title)s\t%(channel)s\t%(webpage_url)s",
        f"ytsearch{args.limit}:{args.query}",
    ]
    if args.proxy:
        cmd[1:1] = ["--proxy", args.proxy]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=SUBPROCESS_ENV)
    if p.returncode != 0 and not p.stdout.strip():
        fail("yt-dlp 搜索失败", stderr=(p.stderr or "")[-3000:])
    candidates = []
    for line in (p.stdout or "").splitlines():
        parts = line.split("\t", 4)
        if len(parts) < 5:
            continue
        vid, duration, title, channel, url = parts
        if not url or url == "NA":
            url = f"https://www.youtube.com/watch?v={vid}"
        try:
            dur = float(duration)
        except (TypeError, ValueError):
            dur = None
        candidates.append({
            "id": vid,
            "duration": dur,
            "title": title,
            "channel": channel,
            "url": url,
            "is_topic": "- Topic" in (channel or ""),
        })
    emit({"ok": True, "query": args.query, "candidates": candidates})


def cmd_download(args) -> None:
    need_tools()
    name = safe_name(args.name)
    INCOMING.mkdir(parents=True, exist_ok=True)
    # 用固定文件名，避免标题里的特殊字符影响 Windows 路径
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"{name}-", dir=str(INCOMING)))
    out_tpl = str(tmp_dir / "%(id)s.%(ext)s")
    cmd = [
        YTDLP,
        "--no-warnings",
        "--no-playlist",
        "--ffmpeg-location", str(Path(FFMPEG).parent),
        "-f", "bestaudio",
        "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "--embed-metadata",
        "-o", out_tpl,
        args.url,
    ]
    if args.proxy:
        cmd[1:1] = ["--proxy", args.proxy]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=SUBPROCESS_ENV)
    if p.returncode != 0:
        fail("yt-dlp 下载失败", stderr=(p.stderr or "")[-4000:])
    mp3s = sorted(tmp_dir.glob("*.mp3"))
    if not mp3s:
        fail("yt-dlp 没有产出 mp3", files=[x.name for x in tmp_dir.iterdir()])
    src = mp3s[-1]
    video_id = src.stem
    meta = {
        "title": args.title,
        "artist": args.artist,
        "album": args.album,
        "source": "youtube",
        "source_url": args.url,
        "source_id": video_id,
        "license": args.license,
        "usage": args.usage,
    }
    result = finish_file(name, src, meta)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    emit(result)


def _http_get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
            "Referer": "https://music.163.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def cmd_netease(args) -> None:
    need_tools()
    name = safe_name(args.name)
    url = f"https://music.163.com/song/media/outer/url?id={args.song_id}.mp3"
    data = _http_get(url)
    if len(data) < 100_000 or data[:2] == b"<!" or b"<html" in data[:500].lower():
        fail("网易云没有返回音频；可能不是 fee=8 免费曲，或需要登录/VIP", bytes=len(data))
    INCOMING.mkdir(parents=True, exist_ok=True)
    tmp = INCOMING / f"{name}.mp3"
    tmp.write_bytes(data)
    meta = {
        "title": args.title,
        "artist": args.artist,
        "album": args.album,
        "source": "netease",
        "source_url": f"https://music.163.com/song?id={args.song_id}",
        "source_id": str(args.song_id),
        "license": args.license,
        "usage": args.usage,
    }
    emit(finish_file(name, tmp, meta))


def cmd_probe(args) -> None:
    path = Path(args.path)
    if not path.exists():
        fail(f"文件不存在: {path}")
    emit({"ok": True, "file": str(path), "probe": probe(path)})


def cmd_adopt(args) -> None:
    """给 resources/music 里已有的音频补 sidecar，不移动文件。"""
    path = Path(args.path)
    if not path.exists():
        fail(f"文件不存在: {path}")
    if path.parent.resolve() != MUSIC.resolve():
        fail(f"adopt 只处理 resources/music 下的文件: {MUSIC}")
    name = safe_name(args.name or path.stem)
    info = probe(path)
    payload = {
        "file": path.name,
        "path": str(path),
        "title": args.title or info["tags"].get("title"),
        "artist": args.artist or info["tags"].get("artist"),
        "album": args.album or info["tags"].get("album"),
        "source": args.source,
        "source_url": args.source_url,
        "source_id": args.source_id,
        "license": args.license,
        "usage": args.usage,
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "probe": info,
    }
    sidecar = write_sidecar(name, payload)
    emit({"ok": True, "file": str(path), "sidecar": str(sidecar), "meta": payload})


def cmd_library(_args) -> None:
    items = []
    for path in sorted(MUSIC.glob("*.json")):
        if path.name in {"vibe-bgm.json", "library.json"}:
            continue
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    out = MUSIC / "library.json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    emit({"ok": True, "library": str(out), "count": len(items), "items": items})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="BGM 获取（Agent 用，输出 JSON）")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="搜索 YouTube，输出候选列表")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=5)
    s.add_argument("--proxy", default=None, help="例如 socks5://127.0.0.1:1080")
    s.set_defaults(func=cmd_search)

    d = sub.add_parser("download", help="从 YouTube 下载并转 MP3")
    d.add_argument("url")
    d.add_argument("--name", required=True, help="入库文件名（ASCII，不含扩展名）")
    d.add_argument("--title", default=None)
    d.add_argument("--artist", default=None)
    d.add_argument("--album", default=None)
    d.add_argument("--license", default="unknown")
    d.add_argument("--usage", default="self-use")
    d.add_argument("--proxy", default=None)
    d.set_defaults(func=cmd_download)

    n = sub.add_parser("netease", help="下载网易云 fee=8 免费低音质版")
    n.add_argument("song_id", type=int)
    n.add_argument("--name", required=True)
    n.add_argument("--title", default=None)
    n.add_argument("--artist", default=None)
    n.add_argument("--album", default=None)
    n.add_argument("--license", default="unknown")
    n.add_argument("--usage", default="self-use")
    n.set_defaults(func=cmd_netease)

    pr = sub.add_parser("probe", help="用 ffprobe 看时长/码率/标签")
    pr.add_argument("path")
    pr.set_defaults(func=cmd_probe)

    ad = sub.add_parser("adopt", help="给 resources/music 里已有的音频补 sidecar")
    ad.add_argument("path")
    ad.add_argument("--name", default=None)
    ad.add_argument("--title", default=None)
    ad.add_argument("--artist", default=None)
    ad.add_argument("--album", default=None)
    ad.add_argument("--source", default="local")
    ad.add_argument("--source-url", default=None)
    ad.add_argument("--source-id", default=None)
    ad.add_argument("--license", default="unknown")
    ad.add_argument("--usage", default="self-use")
    ad.set_defaults(func=cmd_adopt)

    lib = sub.add_parser("library", help="扫描 *.json sidecar，生成 resources/music/library.json")
    lib.set_defaults(func=cmd_library)
    return p


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
