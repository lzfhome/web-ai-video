"""yutto 客户端：定位本地 venv / ffmpeg / 登录态，拼参数并跑进程。

上游：https://github.com/yutto-dev/yutto （GPL-3.0-only，源码在 repos/yutto/）
这里只当外部 CLI 调用，不 import 它的代码。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[3]
LOCAL = AIWORK / "tools" / "local"
VENV = LOCAL / "venv-yutto"
AUTH_FILE = LOCAL / "yutto-auth.toml"
YUTTO_VERSION = "2.3.1"

_BIN = "Scripts" if os.name == "nt" else "bin"
_EXE = ".exe" if os.name == "nt" else ""


def yutto_exe() -> Path | None:
    p = VENV / _BIN / f"yutto{_EXE}"
    return p if p.exists() else None


def venv_python() -> Path:
    return VENV / _BIN / f"python{_EXE}"


def ffmpeg_exe() -> str | None:
    if os.environ.get("FFMPEG"):
        return os.environ["FFMPEG"]
    for d in reversed(sorted((LOCAL / "ffmpeg").glob("*/bin"))):
        p = d / f"ffmpeg{_EXE}"
        if p.exists():
            return str(p)
    return shutil.which("ffmpeg")


def ffprobe_exe() -> str | None:
    ff = ffmpeg_exe()
    if ff:
        p = Path(ff).with_name(f"ffprobe{_EXE}")
        if p.exists():
            return str(p)
    return shutil.which("ffprobe")


def auth_args(sessdata: str | None = None) -> list[str]:
    """SESSDATA 优先，其次项目内的 auth 文件（不写用户目录）。"""
    if sessdata:
        return ["--auth", f"SESSDATA={sessdata}"]
    if AUTH_FILE.exists():
        return ["--auth-file", str(AUTH_FILE)]
    return []


def run(args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    exe = yutto_exe()
    if not exe:
        raise FileNotFoundError(
            "没有安装 yutto。先跑：python cine/media/engines/bilibili.py setup"
        )
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "NO_COLOR": "1",
    }
    return subprocess.run(
        [str(exe), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=timeout,
    )


def version() -> str | None:
    if not yutto_exe():
        return None
    try:
        r = run(["--version"], timeout=30)
        return (r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else None
    except Exception:
        return None


def setup(quiet: bool = False) -> dict:
    """创建 tools/local/venv-yutto 并安装固定版本；不放 C 盘。"""
    if yutto_exe() and version():
        return {"ok": True, "already": True, "version": version(), "venv": str(VENV)}

    base = Path(sys.executable)
    if VENV in base.resolve().parents:
        raise RuntimeError("当前解释器就在 venv-yutto 里，请用项目 Python 运行 setup")

    env = {**os.environ, "PIP_CACHE_DIR": str(LOCAL / "pip-cache")}
    cmd = [str(base), "-m", "venv", str(VENV)]
    if not quiet:
        print("$", " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, check=True, env=env)

    py = venv_python()
    cmd = [
        str(py), "-m", "pip", "install",
        "--quiet", "--disable-pip-version-check",
        f"yutto=={YUTTO_VERSION}",
    ]
    if not quiet:
        print("$", " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, check=True, env=env)
    return {"ok": True, "already": False, "version": version(), "venv": str(VENV)}
