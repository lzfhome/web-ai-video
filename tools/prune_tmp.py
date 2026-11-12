#!/usr/bin/env python3
"""清理 projects 里的可再生中间产物（默认 dry-run）。

保留：
  - narration.wav / timings.json / lesson.json / bgm.json / *.beats.json
  - lesson<id>.mp4（成片）
  - 每课最新的 N 个 picture.mp4（默认 1）

删除：
  - bed.wav / sfx.wav / final_mix.wav / bgm_auto.wav（可从 lesson.json + narration.wav 再生）
  - 旧 picture.mp4
  - lesson*-cover*.mp4（封面中间片）
  - build/qa/、build/esfx/
  - stills/（接触表）

用法：
  python tools/prune_tmp.py                    # 只看能省多少
  python tools/prune_tmp.py --yes              # 执行
  python tools/prune_tmp.py --project sky-blue --yes
  python tools/prune_tmp.py --keep-audio       # 不动音频缓存
"""
import argparse
import re
import shutil
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

AIWORK = Path(__file__).resolve().parents[1]
PROJECTS = AIWORK / "workspaces/vibe-knowledge/projects"
AUDIO = {"bed.wav", "sfx.wav", "final_mix.wav", "bgm_auto.wav"}
COVER = re.compile(r"lesson.*-cover.*\.mp4$", re.I)


def mb(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB"


def old_enough(p: Path, days: float) -> bool:
    return days <= 0 or (time.time() - p.stat().st_mtime) >= days * 86400


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="真正删除；默认 dry-run")
    ap.add_argument("--project", default=None)
    ap.add_argument("--keep-picture", type=int, default=1, help="每课保留最新的 N 个 picture.mp4")
    ap.add_argument("--keep-audio", action="store_true", help="保留 bed/sfx/final_mix/bgm_auto")
    ap.add_argument("--keep-stills", action="store_true", help="保留 stills 接触表")
    ap.add_argument("--older-than", type=float, default=0, help="只处理 N 天前的文件")
    args = ap.parse_args()

    if not PROJECTS.is_dir():
        raise SystemExit(f"没有 {PROJECTS}")

    works = sorted(p for p in PROJECTS.iterdir() if p.is_dir())
    if args.project:
        works = [p for p in works if p.name == args.project]
        if not works:
            raise SystemExit(f"没有项目：{args.project}")

    targets = []  # (path, reason)
    for work in works:
        lessons = [p for p in (work / "lessons").iterdir() if p.is_dir()] if (work / "lessons").is_dir() else []
        for lesson in lessons:
            build = lesson / "build"
            if build.is_dir():
                pictures = sorted(
                    (p for p in build.glob("picture.mp4") if p.is_file() and old_enough(p, args.older_than)),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                keep = {str(p) for p in pictures[:max(0, args.keep_picture)]}
                for p in pictures:
                    if str(p) not in keep:
                        targets.append((p, "旧 picture"))
                for p in build.rglob("*"):
                    if not p.is_file() or not old_enough(p, args.older_than):
                        continue
                    if not args.keep_audio and p.name in AUDIO:
                        targets.append((p, "可再生音频"))
                    elif COVER.match(p.name):
                        targets.append((p, "封面中间片"))
                for d in list(build.rglob("qa")) + list(build.rglob("esfx")):
                    if d.is_dir() and old_enough(d, args.older_than):
                        targets.append((d, "缓存目录"))
            stills = lesson / "stills"
            if stills.is_dir() and not args.keep_stills and old_enough(stills, args.older_than):
                targets.append((stills, "接触表"))

    # 去重（目录和文件可能重复覆盖）
    seen, uniq = set(), []
    for p, why in targets:
        if str(p) in seen:
            continue
        seen.add(str(p))
        uniq.append((p, why))

    total = 0
    for p, why in uniq:
        try:
            size = p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        except OSError:
            size = 0
        total += size
        print(f"{why:8}  {mb(size):>9}  {p.relative_to(AIWORK)}")

    print(f"\n共 {len(uniq)} 项，可释放 {mb(total)}")
    if not args.yes:
        print("这是 dry-run；加 --yes 执行。")
        return 0

    failed = 0
    for p, _ in uniq:
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        except OSError as exc:
            print(f"⚠ 删除失败 {p}: {exc}")
            failed += 1
    print(f"完成：{len(uniq) - failed} 项已删除" + (f"，{failed} 项失败" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
