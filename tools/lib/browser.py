"""cine 工具共用：找无头浏览器（macOS 用 Metal 出图，Linux 用默认 SwiftShader/GPU）。
CINE_CHROME 环境变量优先；否则用 Playwright 缓存里最新的 chromium_headless_shell；都没有就交给 Playwright 默认。"""
import os
import sys
from pathlib import Path

GPU = (["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"]
       if sys.platform == "darwin" else
       ["--no-sandbox", "--enable-gpu", "--ignore-gpu-blocklist"])


def chrome():
    if os.environ.get("CINE_CHROME"):
        return os.environ["CINE_CHROME"]
    patterns = [
        "Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-*/chrome-headless-shell",
        ".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell",
    ]
    for pat in patterns:
        found = sorted(Path.home().glob(pat), key=lambda p: p.parts[-3])
        if found:
            return str(found[-1])
    return None


def launch(p):
    exe = chrome()
    return p.chromium.launch(executable_path=exe, args=GPU) if exe else p.chromium.launch(args=GPU)
