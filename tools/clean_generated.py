#!/usr/bin/env python3
"""只留素材和文本，清理 projects 里的生成物（默认 dry-run）。

保留：
  - project.json、lessons 下的 json / js / md / txt / html / css
  - lessons/**/assets/**（素材）
  - 项目根 source/**（素材）
  - build/text、build/research、build/source 会先移到同级 assets/ 下

删除：
  - build/**、deliveries/**、stills/**、frames/**
  - __pycache__、*.log

用法：
  python tools/clean_generated.py
  python tools/clean_generated.py --yes
  python tools/clean_generated.py --project canghai-six --yes
"""
import argparse
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

AIWORK = Path(__file__).resolve().parents[1]
PROJECTS = AIWORK / "workspaces/vibe-knowledge/projects"
SOURCE_DIRS = ("text", "research", "source")
DELETE_DIRS = ("deliveries", "stills", "frames")


def mb(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB"


def size_of(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def unique_target(dst: Path) -> Path:
    if not dst.exists():
        return dst
    stem, suffix = dst.stem, dst.suffix
    i = 1
    while True:
        cand = dst.with_name(f"{stem}-{i}{suffix}")
        if not cand.exists():
            return cand
        i += 1


def move_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in list(src.iterdir()):
        shutil.move(str(item), str(unique_target(dst / item.name)))
    src.rmdir()


def build_dirs(project: Path) -> list[Path]:
    dirs = []
    root_build = project / "build"
    if root_build.is_dir():
        dirs.append(root_build)
    lessons = project / "lessons"
    if lessons.is_dir():
        for lesson in lessons.iterdir():
            build = lesson / "build"
            if build.is_dir():
                dirs.append(build)
    return dirs


def delete_targets(project: Path) -> list[Path]:
    targets: list[Path] = []
    targets.extend(build_dirs(project))

    for name in DELETE_DIRS:
        root = project / name
        if root.is_dir():
            targets.append(root)
        lessons = project / "lessons"
        if lessons.is_dir():
            for lesson in lessons.iterdir():
                p = lesson / name
                if p.is_dir():
                    targets.append(p)

    for pattern in ("__pycache__",):
        targets.extend(p for p in project.rglob(pattern) if p.is_dir())
    targets.extend(p for p in project.rglob("*.log") if p.is_file())

    # 去掉嵌套项，避免重复统计/删除
    uniq: list[Path] = []
    for p in sorted(set(targets), key=lambda x: len(x.parts)):
        if any(p == q or p.is_relative_to(q) for q in uniq):
            continue
        uniq.append(p)
    return uniq


def source_dirs(build: Path) -> list[Path]:
    return [build / name for name in SOURCE_DIRS if (build / name).is_dir()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="真正删除；默认只预览")
    ap.add_argument("--project", default=None, help="只处理指定项目")
    args = ap.parse_args()

    if not PROJECTS.is_dir():
        raise SystemExit(f"没有 {PROJECTS}")

    works = sorted(p for p in PROJECTS.iterdir() if p.is_dir())
    if args.project:
        works = [p for p in works if p.name == args.project]
        if not works:
            raise SystemExit(f"没有项目：{args.project}")

    total_keep = total_move = total_delete = 0
    rows = []

    for project in works:
        assets = [p for p in project.rglob("assets") if p.is_dir()]
        keep = sum(size_of(p) for p in assets)

        move_paths = [s for b in build_dirs(project) for s in source_dirs(b)]
        move = sum(size_of(p) for p in move_paths)

        targets = delete_targets(project)
        delete = max(0, sum(size_of(p) for p in targets) - move)

        total_keep += keep
        total_move += move
        total_delete += delete
        rows.append((project.name, keep, move, delete, targets, move_paths))

    for name, keep, move, delete, targets, move_paths in rows:
        print(f"{name:22} 素材 {mb(keep):>9}  移出 {mb(move):>7}  删除 {mb(delete):>9}")
        for p in move_paths:
            print(f"    移出  {p.relative_to(AIWORK)}")
        for p in targets:
            print(f"    删除  {p.relative_to(AIWORK)}")

    print()
    print(f"合计：保留素材 {mb(total_keep)}，移出文本 {mb(total_move)}，删除生成物 {mb(total_delete)}")
    if not args.yes:
        print("这是 dry-run；加 --yes 执行。")
        return 0

    moved = deleted = 0
    for _name, _keep, _move, _delete, targets, move_paths in rows:
        for src in move_paths:
            dst = src.parent.parent / "assets" / src.name
            size = size_of(src)
            move_tree(src, dst)
            moved += size
        for p in targets:
            if not p.exists():
                continue
            size = size_of(p)
            shutil.rmtree(p) if p.is_dir() else p.unlink()
            deleted += size

    print(f"完成：移出 {mb(moved)}，删除 {mb(deleted)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
