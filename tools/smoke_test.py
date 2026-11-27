#!/usr/bin/env python3
"""端到端 smoke test：新建 3 秒无声 lesson → timings → record → finish → deliver。

用法：
  python tools/smoke_test.py
  python tools/smoke_test.py --keep    # 保留测试项目，方便看接触表/成片

需要 ffmpeg 在 PATH（或设置 FFMPEG），以及 Playwright Chromium。
成功时清理测试项目；失败时保留并打印路径。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

AIWORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIWORK))
PY = sys.executable

from tools.lib.scaffold import create_project  # noqa: E402
SLUG = f"smoke-{os.getpid()}"
PROJECT = AIWORK / "workspaces/vibe-knowledge/projects" / SLUG
LESSON = PROJECT / "lessons" / SLUG
DELIVERY = PROJECT / "build" / "deliver" / "smoke"


def run(name, cmd, env=None):
    print(f"\n$ {' '.join(map(str, cmd))}")
    p = subprocess.run(list(map(str, cmd)), cwd=AIWORK, env=env)
    if p.returncode != 0:
        raise SystemExit(f"✗ {name} 失败（退出码 {p.returncode}）；测试目录保留：{PROJECT}")


def cleanup():
    shutil.rmtree(PROJECT, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    env = {**os.environ}
    create_project(SLUG, "Smoke Test", "A", "dom-narrated")
    print(f"✓ 临时项目：{PROJECT}")

    (LESSON / "narration.json").write_text(json.dumps({
        "mode": "silent",
        "beats": [
            {"id": "B01", "dur": 1.0, "card": "A"},
            {"id": "B02", "dur": 1.0, "card": "B"},
            {"id": "B03", "dur": 1.0, "card": "C"},
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    run("silent_timings", [PY, "cine/audio/engines/tts_silent.py",
                           LESSON / "narration.json", LESSON / "build"])

    env["CINE_ROOT"] = str(PROJECT)
    run("record", [PY, "cine/video/engines/dom/record.py", SLUG, "--fps", "5", "--to", "2"], env)
    run("finish", [PY, "workspaces/vibe-knowledge/line/dom-narrated/finish.py", SLUG, "--fps", "5"], env)
    run("deliver", [PY, "cine/video/engines/deliver.py", SLUG,
                    "--title", "Smoke Test", "--poster", "1", "--out", str(DELIVERY)], env)

    checks = [
        LESSON / "build" / "picture.mp4",
        LESSON / "build" / f"lesson{SLUG}.mp4",
        LESSON / "build" / "final_mix.wav",
        DELIVERY / "video.mp4",
        DELIVERY / "cover.jpg",
    ]
    missing = [p for p in checks if not p.exists() or p.stat().st_size == 0]
    if missing:
        raise SystemExit("✗ 缺少产物：" + "，".join(str(p) for p in missing) + f"\n测试目录保留：{PROJECT}")

    print("\n✓ smoke test 通过")
    for p in checks:
        print(f"  {p.relative_to(AIWORK)}  {p.stat().st_size / 1024:.0f} KB")

    if args.keep:
        print(f"保留测试项目：{PROJECT}")
    else:
        cleanup()
        print("已清理测试项目。")


if __name__ == "__main__":
    main()
