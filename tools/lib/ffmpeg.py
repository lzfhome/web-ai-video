"""编码器选择：x264（质量优先/默认）或 NVENC（GPU，驱动支持时）。"""
import os
import shutil
import subprocess
from pathlib import Path

FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"


def ffprobe() -> str:
    """优先 FFPROBE 环境变量，其次 ffmpeg 同目录，最后 PATH。"""
    p = os.environ.get("FFPROBE")
    if p:
        return p
    parent = Path(FFMPEG)
    if parent.name.lower().startswith("ffmpeg"):
        cand = parent.with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if cand.exists():
            return str(cand)
    return shutil.which("ffprobe") or "ffprobe"


def probe_duration(path) -> float:
    out = subprocess.run(
        [ffprobe(), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def probe_fps(path, stream: str = "v:0"):
    try:
        r = subprocess.run(
            [ffprobe(), "-v", "error", "-select_streams", stream, "-show_entries", "stream=r_frame_rate",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, check=True,
        )
        num, den = r.stdout.strip().split("/")
        return float(num) / float(den)
    except Exception:
        return None


def nvenc_available() -> bool:
    """真正跑一帧 64x64 测试；驱动/ffmpeg 不匹配时返回 False。"""
    try:
        r = subprocess.run(
            [FFMPEG, "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.04",
             "-frames:v", "1", "-c:v", "h264_nvenc", "-f", "null", "-"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20,
        )
        return r.returncode == 0
    except Exception:
        return False


def vcodec(encoder: str, crf: str):
    if encoder == "nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq",
                "-rc", "vbr", "-cq", str(crf), "-b:v", "0"]
    return ["-c:v", "libx264", "-preset", "slow", "-crf", str(crf)]
