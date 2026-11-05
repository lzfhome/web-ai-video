#!/usr/bin/env python3
"""在 AIWork 里新建一个「作品优先」项目。

用法：
  python3 workspaces/vibe-knowledge/tools/new_project.py my-film --title "我的片子"

会创建：
  projects/my-film/
    project.json
    cine -> ../../workspaces/vibe-knowledge/cine
    lessons/my-film/        # 从 templates/lesson 复制
    design/
  out/_tmp/my-film/{build,stills}
  并给 lessons/my-film/{build,stills} 建软链，指向 out/_tmp/my-film。
"""
import argparse
import json
import os
import shutil
from datetime import date
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[3]
WS = AIWORK / "workspaces/vibe-knowledge"
TEMPLATE = WS / "templates/lesson"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--title", default=None)
    ap.add_argument("--template", default="lesson")
    args = ap.parse_args()

    slug = args.slug.strip()
    title = args.title or slug
    project = AIWORK / "projects" / slug
    if project.exists():
        raise SystemExit(f"项目已存在：{project}")

    lesson = project / "lessons" / slug
    (project / "lessons").mkdir(parents=True)
    shutil.copytree(TEMPLATE, lesson)
    (project / "design").mkdir()

    # 共享引擎
    os.symlink(os.path.relpath(WS / "cine", project), project / "cine")

    # 中间产物放 out/_tmp，源码里只留软链
    build = AIWORK / "out/_tmp" / slug / "build"
    stills = AIWORK / "out/_tmp" / slug / "stills"
    build.mkdir(parents=True, exist_ok=True)
    stills.mkdir(parents=True, exist_ok=True)
    os.symlink(os.path.relpath(build, lesson), lesson / "build")
    os.symlink(os.path.relpath(stills, lesson), lesson / "stills")

    data = {
        "title": title,
        "type": "video",
        "workspace": str((WS).relative_to(AIWORK)),
        "template": args.template,
        "lesson": slug,
        "status": "draft",
        "output": f"out/{slug}/{date.today().isoformat()}_draft",
    }
    (project / "project.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"✓ 项目：{project}")
    print(f"✓ 源码：{lesson}")
    print(f"✓ 中间：{build}")
    print("下一步：")
    print(f"  cd {AIWORK}")
    print(f"  CINE_ROOT=projects/{slug} python3 workspaces/vibe-knowledge/cine/tools/record.py {slug} --fps 30")
    print(f"  CINE_ROOT=projects/{slug} python3 workspaces/vibe-knowledge/cine/tools/finish.py {slug} --fps 30")
    print(f"  成品放：{AIWORK / data['output']}")


if __name__ == "__main__":
    main()
