#!/usr/bin/env python3
"""AIWork 根目录命令：查看已有产物、按产线生成、查看支持的能力。

project 只是产物，不是档案。这里不读/展示项目说明，只做：
  - list     看所有 workspace 下已有的产物
  - lines    看当前支持哪些产线和模板骨架
  - build    读 line/<line>/build.json，新建项目并出片
  - render   按产物自己的 line 生成视频
  - deliver  把成片收进 deliveries/
  - qa       看成片质检

用法：
  python project.py
  python project.py list
  python project.py lines
  python project.py build poetry
  python project.py render sky-blue
  python project.py render sky-blue --line canvas-bgm --fps 30
  python project.py render my-film --line dom-narrated --workers 2
  python project.py render my-poem --line poetry --workers 2
  python project.py deliver sky-blue --title "天空为什么是蓝的？" --poster 1
  python project.py qa sky-blue

新建项目不在这里：line 就是模板，直接复制对应 line 的 skeleton。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

AIWORK = Path(__file__).resolve().parent
sys.path.insert(0, str(AIWORK))

# 本地 ffmpeg 自动入 PATH：换一个 Agent 也不用手工设环境变量
_ff_dirs = sorted((AIWORK / "tools/local/ffmpeg").glob("*/bin"))
_ff_dir = next((d for d in reversed(_ff_dirs) if (d / "ffmpeg.exe").exists()), None)
if _ff_dir and not os.environ.get("FFMPEG"):
    os.environ["FFMPEG"] = str(_ff_dir / "ffmpeg.exe")
    os.environ["PATH"] = str(_ff_dir) + os.pathsep + os.environ.get("PATH", "")

from tools.lib.paths import CINE, project_fps, project_line  # noqa: E402

PY = sys.executable
WORKSPACES = AIWORK / "workspaces"


def iter_projects():
    """所有 workspace 下的产物目录。"""
    if not WORKSPACES.is_dir():
        return
    for ws in sorted(p for p in WORKSPACES.iterdir() if p.is_dir()):
        root = ws / "projects"
        if not root.is_dir():
            continue
        for project in sorted(p for p in root.iterdir() if p.is_dir()):
            if (project / "lessons").is_dir() or (project / "deliveries").is_dir():
                yield ws, project


def resolve_project(name: str):
    hits = [(ws, p) for ws, p in iter_projects() if p.name == name]
    if not hits:
        raise SystemExit(f"找不到产物：{name}（用 python project.py list 看全部）")
    if len(hits) > 1:
        names = "、".join(f"{ws.name}/{p.name}" for ws, p in hits)
        raise SystemExit(f"产物名不唯一：{name}（{names}）")
    return hits[0]


def resolve_lesson(project: Path) -> str:
    try:
        data = json.loads((project / "project.json").read_text(encoding="utf-8"))
        lesson = data.get("lesson")
        if lesson and (project / "lessons" / lesson).is_dir():
            return str(lesson)
    except Exception:
        pass
    lessons = sorted(p.name for p in (project / "lessons").iterdir() if p.is_dir())
    if len(lessons) == 1:
        return lessons[0]
    if not lessons:
        raise SystemExit(f"产物没有 lesson：{project}")
    raise SystemExit(f"lesson 不唯一：{', '.join(lessons)}，请加 --lesson")


def run(script: Path, args: list, cwd: Path | None = None, env: dict | None = None):
    cmd = [PY, str(script), *map(str, args)]
    print("$", " ".join(cmd[1:]))
    subprocess.run(cmd, cwd=cwd or AIWORK, env={**os.environ, **(env or {})}, check=True)


def cmd_list(_a):
    rows = []
    for ws, project in iter_projects():
        deliveries = project / "deliveries"
        outputs = sorted(p.name for p in deliveries.iterdir() if p.is_dir()) if deliveries.is_dir() else []
        rows.append((ws.name, project.name, project_line(project) or "?", outputs))
    if not rows:
        print("还没有产物。")
        return
    for ws, name, line, outputs in rows:
        latest = outputs[-1] if outputs else "—"
        mark = "" if (WORKSPACES / ws / "line" / line).is_dir() else "   (产线已删)"
        print(f"{ws}/{name:22} {line:12} {len(outputs):2} outputs   最新：{latest}{mark}")


def cmd_lines(a):
    if not WORKSPACES.is_dir():
        return
    for ws in sorted(p for p in WORKSPACES.iterdir() if p.is_dir()):
        if a.workspace and ws.name != a.workspace:
            continue
        root = ws / "line"
        if not root.is_dir():
            continue
        for line in sorted(p for p in root.iterdir() if p.is_dir()):
            skeletons = sorted(p.name for p in line.glob("*.skeleton.*"))
            note = ", ".join(skeletons)
            print(f"{ws.name}/{line.name:12} {note or '（无骨架）'}")


def _load_jsonc(path: Path):
    """读带 // 和 /* */ 注释的 JSON（build.json 用这个，方便在参数旁边写中文）。"""
    text = path.read_text(encoding="utf-8").lstrip("\ufeff")
    out, i, n, in_str, esc = [], 0, len(text), False, False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    body = re.sub(r",\s*([}\]])", r"\1", "".join(out))
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise SystemExit(f"{path.name} 格式错误：第 {e.lineno} 行第 {e.colno} 列，{e.msg}")


def _unique_dir(root: Path, base: str) -> str:
    name, i = base, 2
    while (root / name).exists():
        name = f"{base}-v{i}"
        i += 1
    return name


def _asset(line_dir: Path, p: str) -> Path:
    q = Path(p).expanduser()
    if q.is_absolute() and q.exists():
        return q
    for base in (line_dir, AIWORK):
        cand = base / q
        if cand.exists():
            return cand
    raise SystemExit(f"找不到素材：{p}（相对 {line_dir} 或 AIWork 根目录）")


def cmd_build(a):
    """读 line/<line>/build.json：复制骨架、拷素材、生成 poem.json，再渲染交付。"""
    ws = WORKSPACES / a.workspace
    line_dir = ws / "line" / a.line
    spec = line_dir / "build.json"
    if not spec.exists():
        raise SystemExit(f"缺少输入文件：{spec}")

    if getattr(a, "work", None):
        import json as _json
        sys.path.insert(0, str(line_dir))
        from compose import compose as _compose
        work = _json.loads(Path(a.work).read_text(encoding="utf-8"))
        defaults = _json.loads((line_dir / "defaults.json").read_text(encoding="utf-8"))
        data = _compose(work, defaults)
        # 封面/BGM 允许相对 work.json 所在目录
        work_dir = Path(a.work).resolve().parent
        for sc in data.get("scenes", []):
            p = sc.get("cover")
            if p and not Path(p).is_absolute() and (work_dir / p).exists():
                sc["cover"] = str((work_dir / p).resolve())
        bg = data.get("bgm") or {}
        p = bg.get("src")
        if p and not Path(p).is_absolute() and (work_dir / p).exists():
            bg["src"] = str((work_dir / p).resolve())
    else:
        data = _load_jsonc(spec)

    base = a.name or data.get("id") or a.line
    projects = ws / "projects"
    projects.mkdir(parents=True, exist_ok=True)
    name = _unique_dir(projects, base)
    project = projects / name
    lesson = name
    ldir = project / "lessons" / lesson
    for sub in ("assets/img", "assets/audio", "build"):
        (ldir / sub).mkdir(parents=True, exist_ok=True)

    # poetry 的入口在 line/poetry/film.js，作品目录不再拷贝 film.js
    if a.line != "poetry":
        film = line_dir / "film.skeleton.js"
        if not film.exists():
            raise SystemExit(f"缺骨架：{film}")
        shutil.copy2(film, ldir / "film.js")

    poem = dict(data)
    for k in ("fps", "poster", "name"):
        poem.pop(k, None)
    poem["id"] = name
    poem["title"] = data.get("title") or name

    for i, sc in enumerate(poem.get("scenes", [])):
        src = _asset(line_dir, sc["cover"])
        rel = f"img/cover-{i + 1}{src.suffix.lower() or '.jpg'}"
        shutil.copy2(src, ldir / "assets" / rel)
        sc["cover"] = rel

    bgm = poem.get("bgm") or {}
    if bgm.get("src"):
        src = _asset(line_dir, bgm["src"])
        rel = f"audio/bgm{src.suffix.lower() or '.mp3'}"
        shutil.copy2(src, ldir / "assets" / rel)
        bgm["src"] = rel

    (ldir / "poem.json").write_text(
        json.dumps(poem, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if getattr(a, "work", None):
        shutil.copy2(Path(a.work), ldir / "work.json")

    meta = {
        "title": poem["title"],
        "type": "video",
        "workspace": a.workspace,
        "line": a.line,
        "narration": "A",
        "fps": int(data.get("fps", 30)),
        "resolution": "1920x1080",
        "lesson": lesson,
        "status": "draft",
        "version": "v1",
    }
    (project / "project.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"新建 {a.workspace}/{name}  ·  {a.line}")
    print(f"  lessons/{lesson}/poem.json")
    print(f"  lessons/{lesson}/assets/  ← 已复制封面 {len(poem.get('scenes', []))} 张"
          + ("、BGM" if bgm.get("src") else ""))
    if a.no_render:
        print("已跳过渲染（--no-render）")
        return

    env = {"CINE_ROOT": str(project)}
    print()
    run(ws / "line" / a.line / "render.py", [lesson, "--workers", a.workers], cwd=project, env=env)
    run(CINE / "video/engines/deliver.py",
        [lesson, "--title", poem["title"], "--poster", a.poster], cwd=project, env=env)
    print(f"\n完成：{project / 'deliveries'}")


def cmd_render(a):
    ws, project = resolve_project(a.project)
    lesson = a.lesson or resolve_lesson(project)
    lesson_dir = project / "lessons" / lesson
    line = a.line or project_line(project) or "canvas-bgm"
    script = ws / "line" / line / "render.py"
    if not script.exists():
        raise SystemExit(f"这条产线没有 render.py：{script}")

    if line == "canvas-bgm":
        args = [lesson, "--hw", a.hw, "--quality", a.quality, "--port", a.port]
        if a.fps:
            args += ["--fps", a.fps]
        if a.no_bgm:
            args.append("--no-bgm")
    elif line in ("dom-narrated", "poetry", "poetry-tts"):
        args = [lesson, "--workers", a.workers, "--shot", a.shot, "--tts", a.tts,
                "--encoder", a.encoder, "--port", a.port]
        if a.fps:
            args += ["--fps", a.fps]
        if a.t0 is not None:
            args += ["--from", a.t0]
        if a.t1 is not None:
            args += ["--to", a.t1]
        if a.audio_only:
            args.append("--audio-only")
    else:
        raise SystemExit(f"未知产线：{line}（可用 --line）")

    print(f"{ws.name}/{project.name}  ·  {line}  ·  fps {a.fps or project_fps(project)}")
    run(script, args, cwd=project, env={"CINE_ROOT": str(project)})


def cmd_deliver(a):
    ws, project = resolve_project(a.project)
    lesson = a.lesson or resolve_lesson(project)
    args = [lesson, "--title", a.title or lesson, "--poster", a.poster]
    if a.out:
        args += ["--out", a.out]
    if a.reencode:
        args.append("--reencode")
    if a.web:
        args.append("--web")
    run(CINE / "video/engines/deliver.py", args, cwd=project, env={"CINE_ROOT": str(project)})


def cmd_qa(a):
    ws, project = resolve_project(a.project)
    lesson = a.lesson or resolve_lesson(project)
    video = project / "lessons" / lesson / "build" / f"lesson{lesson}.mp4"
    if not video.exists():
        raise SystemExit(f"找不到成片：{video}，先 render")
    qa = AIWORK / "skills/vibe-knowledge/tools/qa.py"
    if not qa.exists():
        raise SystemExit(f"这个 workspace 没有配置 qa：{ws}")
    args = [video, "--every", a.every]
    if a.no_ocr:
        args.append("--no-ocr")
    run(qa, args)


def main():
    ap = argparse.ArgumentParser(
        description="AIWork 根目录命令：查看产物 / 查看产线 / 生成 / 交付 / 质检",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("list", help="看所有 workspace 下已有的产物").set_defaults(func=cmd_list)

    p = sub.add_parser("lines", help="看支持哪些产线和模板骨架")
    p.add_argument("workspace", nargs="?", default=None)
    p.set_defaults(func=cmd_lines)

    p = sub.add_parser("build", help="读 line/<line>/build.json，新建项目并出片")
    p.add_argument("line")
    p.add_argument("--workspace", default="vibe-knowledge")
    p.add_argument("--name", default=None, help="项目名；默认用 build.json 的 id")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--poster", type=float, default=7)
    p.add_argument("--no-render", action="store_true")
    p.add_argument("--work", default=None, help="poetry 的 work.json；给了就忽略 build.json")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("render", help="按产物自己的 line 生成视频")
    p.add_argument("project")
    p.add_argument("--lesson", default=None)
    p.add_argument("--line", default=None,
                   choices=["canvas-bgm", "dom-narrated", "poetry", "poetry-tts"])
    p.add_argument("--fps", type=int, default=None)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--shot", default="jpeg", choices=["jpeg", "png"])
    p.add_argument("--hw", default="no-preference",
                   choices=["no-preference", "prefer-hardware", "prefer-software"])
    p.add_argument("--quality", type=int, default=20_000_000)
    p.add_argument("--tts", default="auto", choices=["auto", "edge", "doubao"])
    p.add_argument("--port", default="8964")
    p.add_argument("--encoder", default="x264", choices=["x264", "nvenc"])
    p.add_argument("--from", dest="t0", default=None)
    p.add_argument("--to", dest="t1", default=None)
    p.add_argument("--audio-only", action="store_true")
    p.add_argument("--no-bgm", action="store_true")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("deliver", help="把成片收进 deliveries/")
    p.add_argument("project")
    p.add_argument("--lesson", default=None)
    p.add_argument("--title", default=None)
    p.add_argument("--poster", type=float, default=12)
    p.add_argument("--out", default=None)
    p.add_argument("--reencode", action="store_true")
    p.add_argument("--web", action="store_true")
    p.set_defaults(func=cmd_deliver)

    p = sub.add_parser("qa", help="看成片质检")
    p.add_argument("project")
    p.add_argument("--lesson", default=None)
    p.add_argument("--every", type=float, default=3)
    p.add_argument("--no-ocr", action="store_true")
    p.set_defaults(func=cmd_qa)

    a = ap.parse_args()
    if not a.cmd:
        ap.print_help()
        return
    a.func(a)


if __name__ == "__main__":
    main()
