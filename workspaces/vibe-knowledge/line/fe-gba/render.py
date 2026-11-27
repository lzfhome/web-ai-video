#!/usr/bin/env python3
"""fe-gba 渲染：帧图（Seedream）→ 视频（Seedance 2.5 flash）。

默认 dry-run：只打印将执行的命令，不调用付费 API。
加 --yes 才真正生成；输出已存在时默认跳过，重跑必须显式 --force。
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

LINE = Path(__file__).resolve().parent
AIWORK = LINE.parents[3]
ARK = AIWORK / "cine/image/engines/ark.py"
PY = sys.executable

sys.path.insert(0, str(LINE))
from preflight import DEFAULTS, resolve, validate  # noqa: E402


def run(cmd, yes: bool):
    print("$", " ".join(str(x) for x in cmd))
    if not yes:
        return
    try:
        subprocess.run([str(x) for x in cmd], cwd=AIWORK, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"✗ 命令失败（exit {exc.returncode}）：先修正参数/描述，不要直接重抽")


def find_shot(work: dict, sid: str) -> dict:
    for i, shot in enumerate(work.get("shots") or []):
        if str(shot.get("id") or f"S{i + 1:02d}") == sid:
            return shot
    raise SystemExit(f"找不到镜头：{sid}")


def main():
    ap = argparse.ArgumentParser(description="fe-gba：帧图 → Seedance 2.5 flash（默认 dry-run）")
    ap.add_argument("lesson")
    ap.add_argument("--root", default=None, help="项目根目录；默认 CINE_ROOT 或当前目录")
    ap.add_argument("--shot", default=None, help="只跑某个镜头 ID")
    ap.add_argument("--yes", action="store_true", help="真正调用付费 API；不加只打印计划")
    ap.add_argument("--force", action="store_true", help="允许覆盖已存在的视频")
    ap.add_argument("--force-keyframe", action="store_true", help="允许覆盖已存在的帧图")
    ap.add_argument("--keyframe-only", action="store_true", help="只生成帧图，不生成视频")
    ap.add_argument("--skip-keyframe", action="store_true", help="跳过帧图，直接用已有帧图生成视频")
    args = ap.parse_args()

    root = Path(args.root or os.environ.get("CINE_ROOT") or Path.cwd()).expanduser().resolve()
    lesson_dir = root / "lessons" / args.lesson
    work_path = lesson_dir / "work.json"
    if not work_path.exists():
        raise SystemExit(f"找不到 work.json：{work_path}")

    work = json.loads(work_path.read_text(encoding="utf-8"))
    errors, warnings, plan = validate(work, lesson_dir)
    for w in warnings:
        print(f"⚠ {w}")
    if errors:
        raise SystemExit("work.json 预检失败：\n  - " + "\n  - ".join(errors))

    shots = [p for p in plan if not args.shot or p["id"] == args.shot]
    if not shots:
        raise SystemExit(f"没有匹配的镜头：{args.shot}")

    print(f"project: {root}")
    print(f"lesson:  {args.lesson}")
    print(f"mode:    {'生成' if args.yes else 'dry-run（加 --yes 才调用 API）'}")
    print(f"shots:   {', '.join(p['id'] for p in shots)}\n")

    for p in shots:
        shot = find_shot(work, p["id"])
        kp = Path(p["keyframe"])
        vp = Path(p["video"])
        refs = [Path(r) for r in p["refs"]]
        mode = p["mode"]

        print(f"== {p['id']} ==")

        # 1) 帧图
        need_keyframe = mode == "first_frame"
        if args.skip_keyframe and need_keyframe and not kp.exists():
            raise SystemExit(f"跳过帧图但文件不存在：{kp}")
        if need_keyframe and not args.skip_keyframe:
            if kp.exists() and not args.force_keyframe:
                print(f"帧图已存在，跳过：{kp}（--force-keyframe 覆盖）")
            else:
                keyframe_model = shot.get("keyframe_model") or DEFAULTS["keyframe_model"]
                keyframe_size = shot.get("keyframe_size") or DEFAULTS["keyframe_size"]
                cmd = [PY, ARK, "image", "--model", keyframe_model,
                       "--prompt", shot["keyframe_prompt"], "--size", keyframe_size,
                       "--out", str(kp)]
                for r in refs:
                    cmd += ["--reference", str(r)]
                if args.yes:
                    cmd.append("--yes")
                run(cmd, args.yes)

        if args.keyframe_only:
            continue

        # 2) 视频
        if vp.exists() and not args.force:
            print(f"视频已存在，跳过：{vp}（--force 覆盖）\n")
            continue
        cmd = [PY, ARK, "video", "--model", p["model"],
               "--prompt", shot["video_prompt"],
               "--duration", str(p["duration"]),
               "--resolution", p["resolution"],
               "--ratio", p["ratio"],
               "--seed", str(p["seed"]),
               "--out", str(vp)]
        if mode == "first_frame":
            if not kp.exists() and not args.yes:
                print(f"⚠ 帧图尚未生成：{kp}（dry-run 只打印计划）")
            cmd += ["--first-frame", str(kp)]
            if p.get("last_frame"):
                cmd += ["--last-frame", p["last_frame"]]
        elif mode == "reference":
            for r in refs:
                cmd += ["--reference", str(r)]
        if shot.get("generate_audio", DEFAULTS["generate_audio"]):
            cmd.append("--generate-audio")
        if args.yes:
            cmd.append("--yes")
        run(cmd, args.yes)
        print()

    if not args.yes:
        print("dry-run 结束：没有调用 Seedream / Seedance。确认后加 --yes。")
    elif args.keyframe_only:
        print("帧图完成。下一步：逐张在 opencode 侧边栏打开，等用户明确确认后再生成视频。")
    else:
        print("视频完成。下一步：逐条在侧边栏打开，跑 qa.py 抽帧审片；重跑必须 --force。")


if __name__ == "__main__":
    main()
