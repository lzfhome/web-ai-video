#!/usr/bin/env python3
"""把已交付的课填进 series.json：视频、封面、时长，并更新上线状态；之后再跑 course_page.py 出课程页。

用法（在项目根跑）：
  CINE_ROOT=workspaces/vibe-knowledge/projects/my-film python cine/video/tools/update_series.py
  python cine/video/tools/update_series.py --root workspaces/vibe-knowledge/projects/my-film --web publish/course --prefix p
课号 = 前缀 + 两位数（如 p03 → publish/course/lessonp03.mp4）；deliver.py 交付时已经按这个名字放好。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")


def arg(k, d):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d


R = Path(arg("--root", os.environ.get("CINE_ROOT") or str(Path.cwd()))).expanduser().resolve()
P = R / "series.json"
WEB = R / arg("--web", "publish/course")
PRE = arg("--prefix", "")
if not P.exists():
    raise SystemExit(f"找不到 {P}\n旧系列才用 series.json；作品优先项目请用 project.json / out 目录。")

S = json.loads(P.read_text(encoding="utf-8"))
done = 0
for les in S["lessons"]:
    n = f"{PRE}{les['n']:02d}"
    v = WEB / f"lesson{n}.mp4"
    if v.exists():
        d = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(v)],
            capture_output=True, text=True, check=True,
        ).stdout)
        les.update(video=v.name, poster=f"lesson{n}.jpg", length=f"{int(d // 60)} 分 {int(round(d % 60))} 秒")
        done += 1
    else:
        for k in ("video", "poster", "length"):
            les.pop(k, None)
total = len(S["lessons"])
S["status_label"] = "全部上线" if done == total else f"已上线 {done}/{total}"
P.write_text(json.dumps(S, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{done}/{total} 节已填入")
