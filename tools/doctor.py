#!/usr/bin/env python3
"""AIWork 环境自检：在跑 cine / video-studio 之前先跑这个。

用法：
  python tools/doctor.py
  python tools/doctor.py --json

检查：
  - Python 版本
  - ffmpeg / ffprobe
  - numpy / scipy / PIL / playwright / edge-tts / fastapi / uvicorn
  - Playwright Chromium
  - cine 字体、默认 BGM
  - video-studio 密钥文件（只检查存在，不读取内容）
  - 仓库根目录是否只有白名单文件（防止临时 html/json 落在根目录）
  - 可选：node、swiftc（OCR）
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

AIWORK = Path(__file__).resolve().parents[1]
CINE = AIWORK / "cine"
BGM = AIWORK / "resources/music/vibe-bgm.m4a"
FONTS = AIWORK / "resources/fonts"
SECRETS = AIWORK / "tools/video-studio/config.secrets.json"

REQUIRED_MODULES = [
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("PIL", "pillow"),
    ("playwright", "playwright"),
    ("edge_tts", "edge-tts"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("pydantic", "pydantic"),
    ("httpx", "httpx"),
    ("multipart", "python-multipart"),
]

results = []


def add(status, name, detail):
    results.append({"status": status, "name": name, "detail": detail})


def check_python():
    v = sys.version_info
    ok = (3, 10) <= (v.major, v.minor)
    add("ok" if ok else "fail", "Python", f"{v.major}.{v.minor}.{v.micro} · {sys.executable}")


def check_ffmpeg():
    for exe in ("ffmpeg", "ffprobe"):
        p = os.environ.get(exe.upper()) or shutil.which(exe)
        if not p:
            # 兼容本仓库里常见的便携安装位置
            for cand in (
                AIWORK / "tools/local/ffmpeg/ffmpeg-9.0.2-essentials_build/bin" / f"{exe}.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/ffmpeg/bin" / f"{exe}.exe",
                AIWORK / "ffmpeg" / "ffmpeg-9.0.2-essentials_build" / "bin" / f"{exe}.exe",
            ):
                if cand.exists():
                    p = str(cand)
                    break
        add("ok" if p else "fail", exe, p or "不在 PATH（装 Gyan.FFmpeg 或设置 FFMPEG/FFPROBE）")


def check_modules():
    for mod, pkg in REQUIRED_MODULES:
        ok = importlib.util.find_spec(mod) is not None
        add("ok" if ok else "fail", pkg, "已安装" if ok else f"缺：python -m pip install {pkg}")


def check_playwright():
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            exe = p.chromium.executable_path
        add("ok" if exe and Path(exe).exists() else "warn", "Playwright Chromium",
            exe if exe and Path(exe).exists() else "缺浏览器：python -m playwright install chromium")
    except Exception as exc:
        add("warn", "Playwright Chromium", f"无法检查：{exc}")


def check_assets():
    dom = CINE / "video/engines/dom/index.html"
    add("ok" if dom.exists() else "fail", "DOM 引擎入口", str(dom) if dom.exists() else "缺失 cine/video/engines/dom/index.html")
    for f in ("NotoSansSC-VF.ttf", "Geist-VF.ttf", "GeistMono-VF.ttf"):
        p = FONTS / f
        add("ok" if p.exists() else "warn", f"字体 {f}", str(p) if p.exists() else "缺失，文字会回退系统字体")
    add("ok" if BGM.exists() else "warn", "默认 BGM", str(BGM) if BGM.exists() else "缺失")
    add("ok" if SECRETS.exists() else "warn", "video-studio 密钥",
        str(SECRETS) if SECRETS.exists() else "缺失（只影响 video-studio / Ark）")


def check_optional():
    add("ok" if shutil.which("node") else "warn", "node", shutil.which("node") or "可选：风格样片/JS 语法检查")
    add("ok" if shutil.which("swiftc") else "warn", "swiftc",
        shutil.which("swiftc") or "可选：qa.py 的 macOS OCR；Windows 会跳过 OCR")


def check_root():
    """根目录只允许白名单文件和目录；多出来的多半是临时产物。"""
    allowed_files = {
        "AGENTS.md", "Process.md", "project.py", "requirements.txt",
        "opencode.json", "opencode.list", ".gitignore", ".gitattributes",
    }
    allowed_dirs = {
        ".git", ".opencode", "__pycache__", "cine", "repos", "resources", "skills", "tools", "workspaces",
    }
    extra = []
    for p in AIWORK.iterdir():
        if p.is_dir():
            if p.name not in allowed_dirs:
                extra.append(p.name + "/")
        elif p.name not in allowed_files:
            extra.append(p.name)
    if extra:
        add("warn", "根目录", "多出 " + "、".join(sorted(extra)) + "（临时件应放 tools/local/<task>/ 或项目 build/）")
    else:
        add("ok", "根目录", "干净（白名单内）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    check_python()
    check_ffmpeg()
    check_modules()
    check_playwright()
    check_assets()
    check_root()
    check_optional()

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        icon = {"ok": "✓", "warn": "⚠", "fail": "✗"}
        for r in results:
            print(f"{icon[r['status']]} {r['name']}: {r['detail']}")
        fails = sum(1 for r in results if r["status"] == "fail")
        warns = sum(1 for r in results if r["status"] == "warn")
        print(f"\n{fails} 个错误，{warns} 个警告")

    return 1 if any(r["status"] == "fail" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
