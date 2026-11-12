#!/usr/bin/env python3
"""产线 dom-narrated：DOM/CSS + Three.js 画面 + 旁白 + BGM → 成片。

流程：timings（silent / edge-tts）→ cine/video/engines/dom/record.py → finish.py

用法：
  CINE_ROOT=workspaces/vibe-knowledge/projects/sangetsuki python line/dom-narrated/render.py 006-text-on-image
  ... render.py 006-text-on-image --fps 30 --workers 4 --shot jpeg
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[4]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

ROOT = Path(os.environ.get("CINE_ROOT") or Path.cwd()).expanduser().resolve()
CINE = AIWORK / "cine"
HERE = Path(__file__).resolve().parent


def run(script: Path, args: list, env: dict):
    cmd = [sys.executable, str(script), *map(str, args)]
    print("$", " ".join(cmd[1:]))
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def ensure_timings(lesson_dir: Path, build: Path, env: dict, tts: str):
    if (build / "timings.json").exists():
        return
    narration = lesson_dir / "narration.json"
    if not narration.exists():
        raise SystemExit("缺少 narration.json / build/timings.json")
    data = json.loads(narration.read_text(encoding="utf-8"))
    voice = data.get("voice") or {}
    mode = data.get("mode")
    if mode == "silent":
        run(CINE / "audio/engines/tts_silent.py", [narration, build], env)
    elif tts == "doubao" or voice.get("engine") == "doubao":
        run(CINE / "audio/engines/tts_doubao.py", [narration, build], env)
    elif tts == "edge" or voice.get("engine") == "edge":
        run(CINE / "audio/engines/tts_edge.py", [narration, build], env)
    else:
        raise SystemExit(
            "缺少 build/timings.json：先配音（--tts edge / --tts doubao），"
            "或把 narration.json 改成 mode: silent"
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lesson")
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--shot", default="jpeg", choices=["jpeg", "png"])
    ap.add_argument("--port", default="8964")
    ap.add_argument("--encoder", default="x264", choices=["x264", "nvenc"])
    ap.add_argument("--tts", default="auto", choices=["auto", "edge", "doubao"])
    ap.add_argument("--from", dest="t0", default=None)
    ap.add_argument("--to", dest="t1", default=None)
    ap.add_argument("--audio-only", action="store_true")
    args = ap.parse_args()

    lesson = args.lesson
    lesson_dir = ROOT / "lessons" / lesson
    build = lesson_dir / "build"
    build.mkdir(parents=True, exist_ok=True)

    fps = args.fps
    if fps is None:
        try:
            fps = int(json.loads((ROOT / "project.json").read_text(encoding="utf-8")).get("fps", 30))
        except Exception:
            fps = 30

    env = {**os.environ, "CINE_ROOT": str(ROOT)}
    print(f"项目：{ROOT}")
    print(f"产线：dom-narrated  fps：{fps}")

    ensure_timings(lesson_dir, build, env, args.tts)

    record_args = [lesson, "--fps", fps, "--workers", args.workers, "--shot", args.shot,
                   "--port", args.port, "--encoder", args.encoder]
    if args.t0 is not None:
        record_args += ["--from", args.t0]
    if args.t1 is not None:
        record_args += ["--to", args.t1]
    run(CINE / "video/engines/dom/record.py", record_args, env)

    finish_args = [lesson, "--fps", fps, "--port", args.port, "--encoder", args.encoder]
    if args.audio_only:
        finish_args.append("--audio-only")
    run(HERE / "finish.py", finish_args, env)


if __name__ == "__main__":
    main()
