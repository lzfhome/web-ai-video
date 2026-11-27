#!/usr/bin/env python3
"""fe-gba QA：ffprobe 检查时长/分辨率/fps，并生成每秒一帧的接触表。

用法：
  python workspaces/vibe-knowledge/line/fe-gba/qa.py <lesson>
  python workspaces/vibe-knowledge/line/fe-gba/qa.py <lesson> --shot S01
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

LINE = Path(__file__).resolve().parent
AIWORK = LINE.parents[3]

# 与 project.py 一致：直接跑 qa.py 时也能找到仓库内的 ffmpeg
_ff_dirs = sorted((AIWORK / "tools/local/ffmpeg").glob("*/bin"))
_ff = next((d / "ffmpeg.exe" for d in reversed(_ff_dirs) if (d / "ffmpeg.exe").exists()), None)
if _ff and not os.environ.get("FFMPEG"):
    os.environ["FFMPEG"] = str(_ff)
    os.environ["PATH"] = str(_ff.parent) + os.pathsep + os.environ.get("PATH", "")

sys.path.insert(0, str(AIWORK))
from tools.lib.ffmpeg import FFMPEG, ffprobe  # noqa: E402

sys.path.insert(0, str(LINE))
from preflight import DEFAULTS, resolve  # noqa: E402


def probe(path: Path) -> dict:
    out = subprocess.run(
        [ffprobe(), "-v", "error", "-show_entries",
         "format=duration,size", "-show_entries",
         "stream=width,height,r_frame_rate,codec_name",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    s = (data.get("streams") or [{}])[0]
    return {
        "duration": float((data.get("format") or {}).get("duration") or 0),
        "size": int((data.get("format") or {}).get("size") or 0),
        "width": int(s.get("width") or 0),
        "height": int(s.get("height") or 0),
        "fps": s.get("r_frame_rate") or "?",
    }


def main():
    ap = argparse.ArgumentParser(description="fe-gba 视频 QA（ffprobe + 接触表）")
    ap.add_argument("lesson")
    ap.add_argument("--root", default=None, help="项目根目录；默认 CINE_ROOT 或当前目录")
    ap.add_argument("--shot", default=None)
    ap.add_argument("--no-contact", action="store_true")
    args = ap.parse_args()

    root = Path(args.root or os.environ.get("CINE_ROOT") or Path.cwd()).expanduser().resolve()
    lesson_dir = root / "lessons" / args.lesson
    work_path = lesson_dir / "work.json"
    if not work_path.exists():
        raise SystemExit(f"找不到 work.json：{work_path}")
    work = json.loads(work_path.read_text(encoding="utf-8"))

    failed = 0
    for i, shot in enumerate(work.get("shots") or []):
        sid = str(shot.get("id") or f"S{i + 1:02d}")
        if args.shot and sid != args.shot:
            continue
        video = resolve(lesson_dir, str(shot.get("video") or f"build/{sid}.mp4"))
        print(f"== {sid} ==")
        if not video.exists():
            print(f"✗ 找不到视频：{video}")
            failed += 1
            continue
        try:
            info = probe(video)
        except Exception as exc:
            print(f"✗ ffprobe 失败：{exc}")
            failed += 1
            continue

        want_res = str(shot.get("resolution") or DEFAULTS["resolution"])
        want_dur = float(shot.get("duration") or DEFAULTS["duration"])
        print(f"  file: {video}")
        print(f"  {info['width']}x{info['height']} · {info['fps']} fps · {info['duration']:.2f}s · {info['size'] / 1048576:.1f} MB")
        if info["duration"] + 0.25 < want_dur:
            print(f"  ⚠ 时长 {info['duration']:.2f}s 短于配置 {want_dur:.1f}s")
        if want_res == "720p" and (info["width"], info["height"]) != (1280, 720):
            print(f"  ⚠ 期望 1280x720，实际 {info['width']}x{info['height']}")
        if want_res == "480p" and (info["width"], info["height"]) not in ((854, 480), (864, 496)):
            print(f"  ⚠ 期望 480p，实际 {info['width']}x{info['height']}")

        if not args.no_contact:
            contact = lesson_dir / "build" / f"{sid}_contact.jpg"
            contact.parent.mkdir(parents=True, exist_ok=True)
            cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", str(video),
                   "-vf", "fps=1,scale=480:-1,tile=5x1", "-frames:v", "1", str(contact)]
            subprocess.run(cmd, check=True)
            print(f"  contact: {contact}")

    if failed:
        raise SystemExit(f"{failed} 个镜头 QA 失败")
    print("✓ QA 完成（人工看接触表：脸、手、武器、动作连续性）")


if __name__ == "__main__":
    main()
