#!/usr/bin/env python3
"""产线 poetry：书封决定背景 + 代码诗句排版 + BGM。

参数只有一份：lessons/<lesson>/poem.json。
本脚本先按 poem.json 的 scenes 生成 narration.json / timings.json（静音时间轴），
再交给 dom-narrated 渲染；所以场景时长和成片时长永远一致，不用手改两处。
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[4]
ROOT = Path(os.environ.get("CINE_ROOT") or Path.cwd()).expanduser().resolve()
CINE = AIWORK / "cine"
DOM = AIWORK / "workspaces/vibe-knowledge/line/dom-narrated/render.py"


def check_poem(data: dict, lesson_dir: Path):
    """poem.json 的基本校验：错误在渲染前说出来，而不是等浏览器报 JS 错。"""
    problems = []
    scenes = data.get("scenes") or []
    if not scenes:
        problems.append("scenes 不能为空")
    for i, sc in enumerate(scenes):
        tag = f"scenes[{i}]"
        if not sc.get("cover"):
            problems.append(f"{tag}.cover 必填")
        elif not (lesson_dir / "assets" / sc["cover"]).exists():
            problems.append(f"{tag}.cover 找不到文件：assets/{sc['cover']}")
        if not (sc.get("line1") or sc.get("lines")):
            problems.append(f"{tag}.line1 或 lines 必填")
        try:
            if not 0 <= float(sc.get("blur", 7)) <= 40:
                problems.append(f"{tag}.blur 需要在 0–40 之间")
        except (TypeError, ValueError):
            problems.append(f"{tag}.blur 不是数字")
    bgm = data.get("bgm") or {}
    if bgm.get("src") and not (lesson_dir / "assets" / bgm["src"]).exists():
        problems.append(f"bgm 找不到文件：assets/{bgm['src']}")
    if problems:
        raise SystemExit("poem.json 有问题：\n  - " + "\n  - ".join(problems))


def sync_poem(lesson_dir: Path, build: Path, env: dict):
    """poem.json → narration.json → timings.json / narration.wav"""
    poem = lesson_dir / "poem.json"
    if not poem.exists():
        raise SystemExit(f"缺少参数文件：{poem}")
    data = json.loads(poem.read_text(encoding="utf-8"))
    check_poem(data, lesson_dir)
    scenes = data.get("scenes") or []
    if not scenes:
        raise SystemExit("poem.json 里没有 scenes")

    base = float(data.get("scene_seconds", 15))
    beats = []
    for i, sc in enumerate(scenes):
        beats.append({
            "id": f"B{i + 1:02d}",
            "dur": float(sc.get("seconds", base)),
            "card": (sc.get("line1") or "")[:12],
        })

    narration = lesson_dir / "narration.json"
    narration.write_text(
        json.dumps({"mode": "silent", "beats": beats}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, str(CINE / "audio/engines/tts_silent.py"), str(narration), str(build)],
        cwd=ROOT, env=env, check=True,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lesson")
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--shot", default="jpeg", choices=["jpeg", "png"])
    ap.add_argument("--tts", default="auto", choices=["auto", "edge"])
    ap.add_argument("--port", default="8964")
    ap.add_argument("--encoder", default="x264", choices=["x264", "nvenc"])
    ap.add_argument("--from", dest="t0", default=None)
    ap.add_argument("--to", dest="t1", default=None)
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--keep-narration", action="store_true",
                    help="不从 poem.json 重建时间轴（给需要真人/配音的版本用）")
    args = ap.parse_args()

    lesson_dir = ROOT / "lessons" / args.lesson
    build = lesson_dir / "build"
    build.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "CINE_ROOT": str(ROOT)}
    if not args.keep_narration:
        sync_poem(lesson_dir, build, env)

    cmd = [sys.executable, str(DOM), args.lesson, "--port", args.port,
           "--workers", str(args.workers), "--shot", args.shot,
           "--tts", args.tts, "--encoder", args.encoder]
    if args.fps:
        cmd += ["--fps", str(args.fps)]
    if args.t0 is not None:
        cmd += ["--from", args.t0]
    if args.t1 is not None:
        cmd += ["--to", args.t1]
    if args.audio_only:
        cmd.append("--audio-only")
    print("poetry → dom-narrated")
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    main()
