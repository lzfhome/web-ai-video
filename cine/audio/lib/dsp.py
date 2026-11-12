"""音频域公共 DSP：旁白包络、ducking、限幅。"""
from __future__ import annotations

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d

from .wavio import SR


def envelope(x: np.ndarray, att: float = 0.04, rel: float = 0.4, sr: int = SR) -> np.ndarray:
    """旁白的平滑包络（0..1），用来压低背景乐。起得快、落得慢。"""
    a = np.abs(x.mean(axis=1))
    win = int(0.05 * sr)
    rms = np.sqrt(np.convolve(a * a, np.ones(win) / win, mode="same"))
    on = (rms > 10 ** (-42 / 20)).astype(np.float64)
    ka, kr = np.exp(-1 / (att * sr)), np.exp(-1 / (rel * sr))
    up = signal.lfilter([1 - ka], [1, -ka], on)
    down = signal.lfilter([1 - kr], [1, -kr], on)
    return np.clip(np.maximum(up, down), 0, 1)


def duck_gain(env: np.ndarray, depth: float = 0.55) -> np.ndarray:
    """说话时把底噪压到 1-depth（0.55 ≈ −7 dB），不说话时回到 1。"""
    return 1.0 - depth * env


def limiter(x: np.ndarray, ceiling: float = 10 ** (-1.5 / 20), look: float = 0.003, sr: int = SR) -> np.ndarray:
    """前瞻峰值限幅：起音即时、释放 50 ms，给 AAC 留 1.5 dB 余量。"""
    peak = np.max(np.abs(x), axis=1)
    n = int(look * sr)
    target = np.minimum(1.0, ceiling / np.maximum(maximum_filter1d(peak, size=2 * n + 1), 1e-9))
    k = np.exp(-1 / (0.05 * sr))
    g = np.minimum(signal.lfilter([1 - k], [1, -k], target - 1) + 1, target)
    return x * g[:, None]
