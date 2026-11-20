#!/usr/bin/env python3
"""通用工具：测 BGM 开头有多长的静音/弱前奏，算出「把长静音裁到 N 秒」的裁剪起点。

任意产线都能用；输出源曲裁剪起点 from 和淡入 fade_in。
poetry 产线直接映射为 work.json 的 bgm_from / bgm_fade_in。

用法：
  python cine/audio/tools/bgm_lead.py <audio> [--keep 1.2] [--threshold -30] [--window 0.25] [--scan 20]
  python cine/audio/tools/bgm_lead.py <audio> --json

输出：
  正拍时间 onset（第一个 RMS ≥ threshold 的窗口）
  裁剪起点 from = max(0, onset - keep)，即裁掉前面的长静音，只留 keep 秒
  淡入 fade_in = 0.1

说明：
  - 是裁剪，不是加静音：原曲 4.5s 才到正拍、想留 1.2s，就写 from=3.3。
  - 不自动改 work.json，只给建议；确认后把字段写进对应产线的配置。
  - 若 onset ≤ keep，说明前奏本来就不长，建议 from=0。
  - 阈值越高越容易把弱前奏当静音；默认 -30 dB 适合钢琴/氛围曲。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(AIWORK))
from tools.lib.ffmpeg import FFMPEG  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="测 BGM 开头静音，给出 bgm_from 裁剪建议")
    ap.add_argument("audio")
    ap.add_argument("--keep", type=float, default=1.2, help="片头保留的静音秒数（默认 1.2）")
    ap.add_argument("--threshold", type=float, default=-30.0, help="视为音乐开始的 RMS dBFS（默认 -30）")
    ap.add_argument("--window", type=float, default=0.25, help="RMS 窗口秒数（默认 0.25）")
    ap.add_argument("--scan", type=float, default=20.0, help="只扫开头多少秒（默认 20）")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    args = ap.parse_args()

    audio = Path(args.audio).expanduser()
    if not audio.is_file():
        raise SystemExit(f"找不到音频：{audio}")

    sr = 8000
    cmd = [FFMPEG, "-v", "error", "-t", f"{args.scan:.3f}", "-i", str(audio),
           "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    if not raw:
        raise SystemExit("ffmpeg 没有解出音频")

    import numpy as np
    a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    step = max(1, int(round(args.window * sr)))
    onset = None
    for i in range(0, len(a) - step + 1, step):
        seg = a[i:i + step]
        rms = 20.0 * np.log10(float(np.sqrt(np.mean(seg ** 2))) + 1e-9)
        if rms >= args.threshold:
            onset = i / sr
            break

    if onset is None:
        result = {"onset": None, "keep": args.keep, "cut": 0.0, "from": 0.0, "fade_in": 0.1,
                  "note": f"开头 {args.scan:g}s 内没有达到 {args.threshold:g} dBFS 的段落"}
    elif onset <= args.keep:
        result = {"onset": round(onset, 3), "keep": args.keep, "cut": 0.0, "from": 0.0, "fade_in": 0.1,
                  "note": f"正拍本来就在 {args.keep:g}s 内，不裁；按默认入场即可"}
    else:
        cut = onset - args.keep
        result = {"onset": round(onset, 3), "keep": args.keep, "cut": round(cut, 3),
                  "from": round(cut, 3), "fade_in": 0.1,
                  "note": f"裁掉前 {cut:.2f}s，保留 {args.keep:g}s 静音过渡；正拍落在片头 {args.keep:g}s"}

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
        return

    print(f"音频：{audio}")
    print(f"正拍：{result['onset'] if result['onset'] is not None else '未找到'}s"
          f"（阈值 {args.threshold:g} dBFS，窗口 {args.window:g}s）")
    print(f"片头保留静音：{args.keep:g}s")
    print(f"源曲裁剪起点：{result['from']}s（裁掉前 {result['cut']:.2f}s）")
    print()
    print("poetry work.json：")
    print(f'  "bgm_from": {result["from"]},')
    print(f'  "bgm_fade_in": {result["fade_in"]}')
    print()
    print(f"其他产线：from={result['from']}, fade_in={result['fade_in']}")
    print(f"\n{result['note']}")


if __name__ == "__main__":
    main()
