"""混音引擎：旁白 + 垫乐（被 duck）+ 点音效 + 片段原声 → final_mix。

只做“把几条已经对齐的轨加在一起 + 响度归一到 −16 dBFS RMS + 限幅”，
不负责生成垫乐/音效/取 BGM；那些是 bed.py、bgm_loop.py 的事。
"""
from __future__ import annotations

import numpy as np

from ..lib.dsp import limiter


def combine(narr: np.ndarray, bed: np.ndarray, sfx: np.ndarray,
            clips: np.ndarray, duck: np.ndarray, sfx_gain: float = 0.9) -> np.ndarray:
    """四条轨等长，duck 是每秒的增益曲线（说话时 <1）。"""
    return narr * 1.0 + bed * duck[:, None] + sfx * sfx_gain + clips


def finalize(mix: np.ndarray, speech: np.ndarray, target_db: float = -16.0) -> np.ndarray:
    """按有旁白的片段把 RMS 对齐到 target_db，再过限幅。"""
    seg = mix[speech] if speech.any() else mix
    rms = float(np.sqrt(np.mean(seg ** 2)))
    mix = mix * (10 ** (target_db / 20) / max(rms, 1e-9))
    return limiter(mix)
