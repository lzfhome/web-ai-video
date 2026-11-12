"""豆包语音合成（Seed-TTS 2.0）封装。

真正的请求逻辑在 cine/audio/clients/doubao_tts.py，这里只做三件事：
  · 把 cine 加到 sys.path 后复用同一份实现，避免两处参数漂移
  · 用线程包一层，给 FastAPI 的 async 路由用
  · 把 config.secrets.json 里的 tts_api_key 透传进去
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from config import CONFIG

AIWORK = Path(__file__).resolve().parents[2]
if str(AIWORK) not in sys.path:
    sys.path.insert(0, str(AIWORK))

from cine.audio.clients.doubao_tts import VOICES, synth  # noqa: E402


def voices() -> list[dict]:
    return [{"id": vid, "name": name, "gender": gender} for vid, (name, gender) in VOICES.items()]


def _key() -> str | None:
    return CONFIG.get("tts_api_key") or None


async def synthesize(text: str, voice: str, *, speed: float = 1.0,
                     emotion: str | None = None, sample_rate: int = 24000,
                     fmt: str = "mp3") -> bytes:
    return await asyncio.to_thread(
        synth, text, voice,
        speed=speed, emotion=emotion, sample_rate=sample_rate, fmt=fmt, key=_key(),
    )
