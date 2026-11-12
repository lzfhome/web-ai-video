"""Windows 控制台兼容：避免 ✓ / → 在 GBK 下抛 UnicodeEncodeError。"""
import sys


def fix():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
