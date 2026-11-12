#!/usr/bin/env python3
"""出片后交付：<project>/deliveries/<日期>_<版本>/{video.mp4, cover.jpg, post.txt, notes.md}。

用法：
  CINE_ROOT=workspaces/vibe-knowledge/projects/my-film python cine/video/engines/deliver.py <课号> --title "片名" --poster 12
  ... deliver.py <课号> --title "片名" --out deliveries/2026-11-10_v1
  默认 video.mp4 直接 copy 视频流（不二次压缩）；要压分享版加 --reencode，要网页版加 --web。
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

ROOT = Path(os.environ.get("CINE_ROOT") or Path.cwd()).expanduser().resolve()


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法：deliver.py <课号> [--title 片名] [--poster 12] [--out 目录] [--web]")
    lesson = sys.argv[1]
    title = arg("--title", lesson)
    poster = arg("--poster", "12")
    src = ROOT / "lessons" / lesson / "build" / f"lesson{lesson}.mp4"
    if not src.exists():
        raise SystemExit(f"找不到成片：{src}\n先跑 render / finish")

    out_arg = arg("--out", None)
    if out_arg:
        out = Path(out_arg).expanduser()
        if not out.is_absolute():
            out = ROOT / out
    else:
        pj = ROOT / "project.json"
        data = json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else {}
        version = data.get("version") or "final"
        out = ROOT / "deliveries" / f"{date.today().isoformat()}_{version}"
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    ffmpeg = shutil.which("ffmpeg") or os.environ.get("FFMPEG")
    if not ffmpeg:
        raise SystemExit("找不到 ffmpeg：装 Gyan.FFmpeg 或设置 FFMPEG")

    video = out / "video.mp4"
    if "--reencode" in sys.argv:
        subprocess.run([
            ffmpeg, "-y", "-loglevel", "error", "-i", str(src),
            "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "6M", "-bufsize", "12M",
            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(video),
        ], check=True)
    else:
        # 默认不再二次压缩：成片已经是最终编码，直接换容器。
        subprocess.run([
            ffmpeg, "-y", "-loglevel", "error", "-i", str(src),
            "-c", "copy", "-movflags", "+faststart", str(video),
        ], check=True)

    cover = out / "cover.jpg"
    subprocess.run([
        ffmpeg, "-y", "-loglevel", "error", "-ss", str(poster), "-i", str(src),
        "-frames:v", "1", "-vf", "scale=1280:-2", "-q:v", "3", str(cover),
    ], check=True)

    if "--web" in sys.argv:
        subprocess.run([
            ffmpeg, "-y", "-loglevel", "error", "-i", str(src),
            "-vf", "scale=1280:-2,fps=30,hqdn3d=3:2:5:4",
            "-c:v", "libx264", "-preset", "slow", "-crf", "29", "-maxrate", "520k", "-bufsize", "1040k",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "64k", "-ac", "1",
            "-movflags", "+faststart", str(out / "video_720p.mp4"),
        ], check=True)

    post = out / "post.txt"
    if not post.exists():
        post.write_text(f"{title}\n", encoding="utf-8")
    notes = out / "notes.md"
    if not notes.exists():
        notes.write_text(f"# {title}\n\n- 成片：`video.mp4`\n- 封面：`cover.jpg`\n", encoding="utf-8")

    print(f"✓ 交付：{out}")
    for p in (video, cover, post, notes):
        print(f"  {p.name}  {p.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
