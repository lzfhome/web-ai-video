#!/usr/bin/env python3
"""配音后检查逐字时间有没有「断」：一长串字挤在同一时刻 = 对齐从那里失败了（常见原因：英文名带连字符、旁白和读音差太多）。

用法：
  CINE_ROOT=workspaces/vibe-knowledge/projects/my-film python cine/audio/tools/check_timings.py <课号>
  python tools/check_timings.py <课号> --root projects/my-film
"""
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")


def parse_args():
    args = sys.argv[1:]
    root = os.environ.get("CINE_ROOT") or str(Path.cwd())
    lesson = None
    i = 0
    while i < len(args):
        if args[i] == "--root" and i + 1 < len(args):
            root = args[i + 1]
            i += 2
        elif args[i].startswith("--"):
            i += 1
        else:
            lesson = args[i]
            i += 1
    if not lesson:
        raise SystemExit("用法：check_timings.py <课号> [--root <项目根>]")
    return Path(root).expanduser().resolve(), lesson


R, L = parse_args()
p = R / "lessons" / L / "build" / "timings.json"
if not p.exists():
    raise SystemExit(f"找不到 {p}\n先配音，或设置 CINE_ROOT / --root 指向项目根。")

t = json.loads(p.read_text(encoding="utf-8"))
bad = 0
for b, bt in t["beats"].items():
    ch, txt, run = bt["chars"], bt["text"], 0
    for i in range(1, len(ch)):
        run = run + 1 if abs(ch[i] - ch[i - 1]) < 1e-6 and txt[i].strip() else 0
        if run == 8:
            bad += 1
            print(f"{b}：从「{txt[i - 8:i + 8]}」开始对齐断了（卡在 {ch[i]:.2f}s，这一拍结束 {bt['end']:.2f}s）")
            break
    cues = bt.get("cues", {})
    late = [k for k, v in cues.items() if v >= bt["end"] - 0.02]
    if late:
        print(f"{b}：这些 cue 落在拍尾，多半是对齐断了：{late}")
print("没有发现问题" if not bad else f"{bad} 拍有问题：改旁白写法后删 build/audio/<拍>.* 重配")
