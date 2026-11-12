#!/usr/bin/env python3
"""内部脚手架：给 smoke test 等自动化创建临时项目。

普通新建项目不需要 CLI：`line` 就是模板，直接复制产线目录里的 skeleton。
不再创建项目级 cine 链接：/cine/* 由 tools/lib/server.py 映射到共享引擎。
也不再创建 out/_tmp 链接：build / stills 就在 lesson 目录里。
"""
import json
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

AIWORK = Path(__file__).resolve().parents[2]
WS = AIWORK / "workspaces/vibe-knowledge"
PROJECTS = WS / "projects"
LINE = WS / "line"
SKILL_TPL = AIWORK / "skills/vibe-knowledge/templates"

# line 就是模板：每条产线自带骨架。
SKELETONS = {
    "canvas-bgm": (LINE / "canvas-bgm/film.canvas.skeleton.js", "film.canvas.js"),
    "dom-narrated": (LINE / "dom-narrated/film.skeleton.js", "film.js"),
    "poetry": (LINE / "poetry/film.skeleton.js", "film.js"),
}


def create_project(slug: str, title: str | None = None, narration: str = "A",
                   line: str = "canvas-bgm") -> Path:
    slug = slug.strip()
    if not slug or any(c in slug for c in '\\/:*?"<>|'):
        raise SystemExit(f"slug 不能包含路径字符：{slug!r}")
    title = title or slug
    if line not in SKELETONS:
        raise SystemExit(f"未知产线：{line}（{' / '.join(SKELETONS)}）")

    project = PROJECTS / slug
    if project.exists():
        raise SystemExit(f"项目已存在：{project}")

    lesson = project / "lessons" / slug
    lesson.mkdir(parents=True)
    (project / "design").mkdir()

    # 产线骨架 → lesson
    src, dest_name = SKELETONS[line]
    if not src.exists():
        raise SystemExit(f"产线骨架缺失：{src}")
    (lesson / dest_name).write_text(
        src.read_text(encoding="utf-8")
        .replace("__ID__", slug)
        .replace("__TITLE__", title)
        .replace("__TPL__", narration),
        encoding="utf-8",
    )

    # 旁白母版 + 事实清单（skill 里的方法论资产）
    narr_src = SKILL_TPL / "narration" / f"{narration}.json"
    if narr_src.exists():
        shutil.copyfile(narr_src, lesson / "narration.json")
    facts_src = SKILL_TPL / "facts.md"
    if facts_src.exists():
        shutil.copyfile(facts_src, lesson / "facts.md")

    for d in ("assets/img", "assets/clips", "assets/audio"):
        (lesson / d).mkdir(parents=True, exist_ok=True)

    data = {
        "title": title,
        "type": "video",
        "workspace": WS.relative_to(AIWORK).as_posix(),
        "line": line,
        "narration": narration,
        "fps": 30,
        "resolution": "1920x1080",
        "lesson": slug,
        "status": "draft",
        "version": "draft",
    }
    (project / "project.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return project



