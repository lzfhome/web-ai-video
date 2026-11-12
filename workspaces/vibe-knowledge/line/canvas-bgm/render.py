#!/usr/bin/env python3
"""产线 canvas-bgm：BGM-only 知识片 → WebCodecs → MP4 → 加 BGM。

用法：
  CINE_ROOT=workspaces/vibe-knowledge/projects/sky-blue python line/canvas-bgm/render.py sky-blue
  ... render.py sky-blue --fps 60
  ... render.py sky-blue --hw prefer-hardware
  ... render.py sky-blue --no-bgm

前置：lesson 里有 film.canvas.js（导出 duration / fps / images / build）。
输出：lessons/<lesson>/build/lesson<lesson>.mp4
"""
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(AIWORK))
from playwright.sync_api import sync_playwright

from tools.lib.browser import launch
from tools.lib.ffmpeg import FFMPEG
from tools.lib.server import serve

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

ROOT = Path(os.environ.get("CINE_ROOT") or Path.cwd()).expanduser().resolve()
BGM = AIWORK / "resources/music/vibe-bgm.m4a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lesson")
    ap.add_argument("--port", default="8964")
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--quality", type=int, default=20_000_000)
    ap.add_argument("--hw", choices=["no-preference", "prefer-hardware", "prefer-software"], default="no-preference")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-bgm", action="store_true")
    ap.add_argument("--bgm", default=str(BGM))
    args = ap.parse_args()

    lesson = args.lesson
    build = ROOT / "lessons" / lesson / "build"
    build.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else build / f"lesson{lesson}.mp4"
    raw = build / "canvas_raw.mp4"

    with serve(int(args.port), ROOT):
        with sync_playwright() as p:
            b = launch(p)
            pg = b.new_page(viewport={"width": 1920, "height": 1080})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{args.port}/cine/canvas/index.html?film=/lessons/{lesson}/film.canvas.js")
            pg.wait_for_function("window.ready || window.__error", timeout=60000)
            err = pg.evaluate("window.__error || null")
            if err:
                b.close()
                raise SystemExit(f"film.canvas.js 加载失败：\n{err}")
            info = pg.evaluate("window.__filmCanvas")
            fps = args.fps or int(info["fps"])
            duration = float(info["duration"])

            t0 = time.perf_counter()
            data = pg.evaluate(
                "(o) => window.renderFilm(o)",
                {"fps": fps, "duration": duration, "quality": args.quality,
                 "hardwareAcceleration": args.hw},
            )
            render_s = time.perf_counter() - t0
            raw.write_bytes(base64.b64decode(data))
            b.close()

    if errs:
        print("页面报错：", errs[:5])

    mux_s = 0.0
    if args.no_bgm or not Path(args.bgm).exists():
        shutil.copyfile(raw, out)
    else:
        t0 = time.perf_counter()
        subprocess.run([
            FFMPEG, "-y", "-loglevel", "error",
            "-i", str(raw), "-i", args.bgm,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-af", "volume=0.7", "-c:a", "aac", "-b:a", "192k",
            "-t", f"{duration:.3f}", "-shortest", "-movflags", "+faststart", str(out),
        ], check=True)
        mux_s = time.perf_counter() - t0

    report = {
        "lesson": lesson,
        "line": "canvas-bgm",
        "fps": fps,
        "duration": duration,
        "frames": round(duration * fps),
        "hardware_acceleration": args.hw,
        "render_s": round(render_s, 2),
        "mux_s": round(mux_s, 2),
        "total_s": round(render_s + mux_s, 2),
        "output": str(out),
    }
    (build / "canvas_timing.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"render+encode: {render_s:.2f}s")
    print(f"bgm mux:       {mux_s:.2f}s")
    print(f"total:         {render_s + mux_s:.2f}s")
    print(f"output:        {out}")


if __name__ == "__main__":
    main()
