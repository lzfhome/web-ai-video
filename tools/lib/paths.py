"""统一的路径解析：AIWork / 共享引擎 / 资源 / 车间 / 产物。"""
import json
import os
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[2]
CINE = AIWORK / "cine"
RESOURCES = AIWORK / "resources"
WS = AIWORK / "workspaces/vibe-knowledge"
PROJECTS = WS / "projects"
LINE = WS / "line"


def cine_root() -> Path:
    """CINE_ROOT（项目根），默认当前目录。"""
    return Path(os.environ.get("CINE_ROOT") or Path.cwd()).expanduser().resolve()


def find_project(lesson: str) -> Path:
    """按 lesson 名在 projects/<work>/lessons/<lesson> 里找唯一项目。"""
    if not PROJECTS.is_dir():
        raise SystemExit(f"还没有项目：{PROJECTS}")
    hits = [p for p in PROJECTS.iterdir() if (p / "lessons" / lesson).is_dir()]
    if not hits:
        raise SystemExit(f"找不到 lesson：{lesson}（{PROJECTS}/*/lessons/{lesson}）")
    if len(hits) > 1:
        names = "、".join(p.name for p in hits)
        raise SystemExit(f"lesson 名不唯一：{lesson}（{names}），请先手动指定项目")
    return hits[0]


def project_fps(project: Path, default: int = 30) -> int:
    try:
        return int(json.loads((project / "project.json").read_text(encoding="utf-8")).get("fps", default))
    except Exception:
        return default


def project_line(project: Path) -> str | None:
    """读 project.json 的 line；没写就按 lesson 文件自动判断。"""
    try:
        line = json.loads((project / "project.json").read_text(encoding="utf-8")).get("line")
        if line:
            return str(line)
    except Exception:
        pass
    for lesson in sorted((project / "lessons").iterdir()):
        if not lesson.is_dir():
            continue
        if (lesson / "film.canvas.js").exists():
            return "canvas-bgm"
        if (lesson / "film.js").exists():
            return "dom-narrated"
    return None
