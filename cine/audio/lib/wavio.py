"""WAV 读写与重采样（48 kHz / 立体声 / 16-bit 是 cine 的统一格式）。"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000


def read_wav(p: str | Path) -> np.ndarray:
    """读 WAV → float64 (n, 2)，自动重采样到 48 kHz、单声道转立体声。"""
    with wave.open(str(p), "rb") as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64).reshape(-1, ch) / 32768.0
    if sr != SR:
        x = signal.resample_poly(x, SR, sr, axis=0)
    return x if ch == 2 else np.repeat(x, 2, axis=1)


def write_wav(p: str | Path, x: np.ndarray) -> None:
    """float64 (n, 2) → 16-bit WAV，超出 ±1 自动削顶。"""
    y = np.clip(np.round(x * 32767.0), -32768, 32767).astype(np.int16)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y.tobytes())


def fit_to(x: np.ndarray, n: int) -> np.ndarray:
    """补零或截断到 n 个采样点。"""
    return np.pad(x, ((0, max(0, n - len(x))), (0, 0)))[:n]
