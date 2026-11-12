#!/usr/bin/env python3
"""兼容入口：Ark/Seedream/Seedance 适配器已移到 cine/image/ark.py。"""
import sys
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(AIWORK))

from cine.image.ark import main  # noqa: E402

if __name__ == "__main__":
    main()
