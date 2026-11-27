#!/usr/bin/env python3
"""fe-gba 冒烟测试：建临时项目 → 占位图 → preflight → render dry-run；不调用付费 API。

用法：
  python workspaces/vibe-knowledge/line/fe-gba/smoke_test.py
  python workspaces/vibe-knowledge/line/fe-gba/smoke_test.py --keep
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

LINE = Path(__file__).resolve().parent
AIWORK = LINE.parents[3]
PY = sys.executable
SLUG = f"fe-gba-smoke-{os.getpid()}"
PROJECT = AIWORK / "workspaces/vibe-knowledge/projects" / SLUG
LESSON = PROJECT / "lessons" / SLUG


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    (LESSON / "assets").mkdir(parents=True, exist_ok=True)
    (LESSON / "build").mkdir(parents=True, exist_ok=True)

    from PIL import Image, ImageDraw

    for name in ("ref.png", "S01_keyframe.png"):
        im = Image.new("RGB", (640, 360), (36, 32, 28))
        d = ImageDraw.Draw(im)
        d.rectangle((240, 80, 400, 320), fill=(180, 120, 60))
        d.ellipse((280, 40, 360, 120), fill=(210, 170, 120))
        im.save(LESSON / "assets" / name if name == "ref.png" else LESSON / "build" / name)

    work = {
        "title": "fe-gba smoke",
        "source": "smoke",
        "story": "占位角色站在石砌庭院中，测试预检和 dry-run。",
        "style": "GBA 火焰纹章官方插画风格，赛璐璐上色，清晰轮廓",
        "style_lock": "占位角色，不追求还原",
        "characters": {"Test": "assets/ref.png"},
        "shots": [{
            "id": "S01",
            "title": "smoke",
            "story": "占位角色站在石砌庭院中，镜头缓慢推近。",
            "reference_images": ["assets/ref.png"],
            "keyframe": "build/S01_keyframe.png",
            "keyframe_prompt": "16:9 构图，GBA 火焰纹章官方插画风格，占位角色站在石砌庭院中，暖色夕阳，完整人物，无文字，无 UI。",
            "video_prompt": "从首帧开始，占位角色缓慢抬头，披风轻轻摆动，镜头缓慢推近；保持人物形状和颜色一致；无文字，无 UI，无水印。",
            "action": {"start": "站定", "middle": "抬头", "end": "看向镜头"},
            "camera": "slow push-in, eye level, 16:9",
            "mode": "first_frame",
            "duration": 5,
            "resolution": "720p",
            "ratio": "16:9",
            "seed": 20261125,
            "generate_audio": False,
        }],
    }
    (LESSON / "work.json").write_text(json.dumps(work, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PROJECT / "project.json").write_text(json.dumps({
        "title": "fe-gba smoke",
        "type": "video",
        "workspace": "vibe-knowledge",
        "line": "fe-gba",
        "narration": "A",
        "fps": 24,
        "resolution": "1280x720",
        "lesson": SLUG,
        "status": "draft",
        "version": "v1",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    env = {**os.environ, "CINE_ROOT": str(PROJECT), "PYTHONIOENCODING": "utf-8"}
    try:
        print("$ preflight")
        p = subprocess.run([PY, str(LINE / "preflight.py"), str(LESSON / "work.json")],
                           cwd=AIWORK, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        print(p.stdout)
        if p.returncode:
            print(p.stderr, file=sys.stderr)
            raise SystemExit("✗ preflight 失败")
        if "✓ 预检通过" not in p.stdout:
            raise SystemExit("✗ preflight 没有打印通过")

        print("$ render --dry-run")
        p = subprocess.run([PY, str(LINE / "render.py"), SLUG],
                           cwd=AIWORK, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        print(p.stdout)
        if p.returncode:
            print(p.stderr, file=sys.stderr)
            raise SystemExit("✗ render dry-run 失败")
        if "dry-run" not in p.stdout or "ark.py video" not in p.stdout:
            raise SystemExit("✗ render 没有打印完整的 dry-run 计划")
        print("\n✓ fe-gba smoke test 通过（未调用 API）")
    finally:
        if args.keep:
            print(f"保留测试项目：{PROJECT}")
        else:
            shutil.rmtree(PROJECT, ignore_errors=True)


if __name__ == "__main__":
    main()
