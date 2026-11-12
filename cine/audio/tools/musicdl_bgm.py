#!/usr/bin/env python3
"""网易云 BGM 获取（musicdl 引擎，Agent 用）。

依赖：D:\\AIWork\\tools\\local\\musicdl（pip --target 安装）
输出：JSON；下载写入 resources/music/<name>.mp3（可选保留 FLAC）。

示例：
  python cine/audio/tools/musicdl_bgm.py search "花火が瞬く夜に 羽肿"
  python cine/audio/tools/musicdl_bgm.py download --query "花火が瞬く夜に 羽肿" \
      --id 434902428 --name hanabi_yuzhong_flac --keep-flac
  python cine/audio/tools/musicdl_bgm.py download --query "Rainy Blue 蓝色阴雨" \
      --id 1341912654 --name rainy-blue_fanwan --keep-flac
"""
from __future__ import annotations

import argparse
import contextlib
import io
import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MUSICDL = ROOT / "tools" / "local" / "musicdl"
if str(MUSICDL) not in sys.path:
    sys.path.insert(0, str(MUSICDL))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from get_bgm import FFMPEG, INCOMING, MUSIC, emit, fail, probe, safe_name, write_sidecar  # noqa: E402

logging.disable(logging.CRITICAL)

from musicdl import musicdl  # noqa: E402


def _silent_search(query: str):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        client = musicdl.MusicClient(music_sources=["NeteaseMusicClient"])
        return client.search(query)


def _song_dict(s) -> dict:
    return {
        "id": getattr(s, "identifier", None),
        "name": getattr(s, "song_name", None),
        "singers": getattr(s, "singers", None),
        "album": getattr(s, "album", None),
        "duration": getattr(s, "duration", None),
        "duration_s": getattr(s, "duration_s", None),
        "ext": getattr(s, "ext", None),
        "size": getattr(s, "file_size", None),
        "url": getattr(s, "download_url", None),
    }


def cmd_search(args) -> None:
    try:
        res = _silent_search(args.query)
    except Exception as exc:
        fail(f"musicdl 搜索失败: {type(exc).__name__}: {exc}")
    songs = res.get("NeteaseMusicClient", [])[: args.limit]
    emit({"ok": True, "query": args.query, "candidates": [_song_dict(s) for s in songs]})


def _download_file(url: str, dest: Path) -> int:
    import requests

    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = 0
        with dest.open("wb") as f:
            for chunk in r.iter_content(1024 * 256):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)
    return total


def _to_mp3(src: Path, dest: Path) -> None:
    if not FFMPEG:
        fail("找不到 ffmpeg")
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-codec:a", "libmp3lame", "-b:a", "320k",
        "-ar", "48000", "-ac", "2",
        str(dest),
    ]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        fail("ffmpeg 转 MP3 失败", stderr=p.stderr.decode("utf-8", errors="replace")[-3000:])


def cmd_download(args) -> None:
    name = safe_name(args.name)
    try:
        res = _silent_search(args.query)
    except Exception as exc:
        fail(f"musicdl 搜索失败: {type(exc).__name__}: {exc}")
    songs = res.get("NeteaseMusicClient", [])
    song = next((s for s in songs if getattr(s, "identifier", None) == args.id), None)
    if song is None:
        fail("没有在搜索结果里找到指定 id", requested_id=args.id, candidates=[_song_dict(s) for s in songs])
    url = getattr(song, "download_url", None)
    ext = (getattr(song, "ext", None) or "").lower()
    if not url:
        fail("musicdl 没有返回下载 URL", song=_song_dict(song))
    if ext not in {"flac", "mp3"}:
        fail(f"不支持的音频格式: {ext}", song=_song_dict(song))

    INCOMING.mkdir(parents=True, exist_ok=True)
    src = INCOMING / f"{name}.{ext}"
    try:
        size = _download_file(url, src)
    except Exception as exc:
        fail(f"下载失败: {type(exc).__name__}: {exc}", url=url)
    if size < 100_000:
        fail("下载文件过小，可能 URL 已过期", bytes=size)

    lossless = None
    if args.format == "flac":
        if ext != "flac":
            fail("源不是 FLAC，不能输出 FLAC", ext=ext)
        final = MUSIC / f"{name}.flac"
        src.replace(final)
    else:
        final = MUSIC / f"{name}.mp3"
        if ext == "mp3":
            src.replace(final)
        else:
            _to_mp3(src, final)
            if args.keep_flac:
                lossless = MUSIC / f"{name}.flac"
                src.replace(lossless)
            else:
                src.unlink(missing_ok=True)

    info = probe(final)
    meta = {
        "title": args.title or getattr(song, "song_name", None),
        "artist": args.artist or getattr(song, "singers", None),
        "album": args.album or getattr(song, "album", None),
        "source": "netease-musicdl",
        "source_url": args.source_url or f"https://music.163.com/song?id={args.id}",
        "source_id": str(args.id),
        "license": args.license,
        "usage": args.usage,
        "lossless_file": lossless.name if lossless else None,
    }
    sidecar = write_sidecar(name, {
        "file": final.name,
        "path": str(final),
        **meta,
        "acquired_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "probe": info,
    })
    emit({"ok": True, "file": str(final), "sidecar": str(sidecar), "bytes": size, "meta": meta, "probe": info})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="网易云 BGM 获取（musicdl，Agent 用，输出 JSON）")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="搜索网易云，输出候选")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_search)

    d = sub.add_parser("download", help="按 id 下载网易云音频，默认转 320k MP3")
    d.add_argument("--query", required=True, help="用来搜索的关键词")
    d.add_argument("--id", required=True, type=int, help="网易云 song id")
    d.add_argument("--name", required=True, help="输出文件名（ASCII，不含扩展名）")
    d.add_argument("--title", default=None)
    d.add_argument("--artist", default=None)
    d.add_argument("--album", default=None)
    d.add_argument("--source-url", default=None)
    d.add_argument("--license", default="unknown")
    d.add_argument("--usage", default="self-use")
    d.add_argument("--format", choices=["mp3", "flac"], default="mp3")
    d.add_argument("--keep-flac", action="store_true", help="转 MP3 时同时保留 FLAC")
    d.set_defaults(func=cmd_download)
    return p


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
