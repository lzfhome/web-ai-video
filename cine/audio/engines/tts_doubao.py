#!/usr/bin/env python3
"""豆包语音配音 + 逐字近似对齐 + timings.json / narration.wav（给 cine 引擎用）。

用法：
  python cine/audio/engines/tts_doubao.py <lesson>/narration.json <lesson>/build

narration.json 里 voice 写：
  {"engine":"doubao","voice":"zh_male_qingcang_uranus_bigtts","speed":0.92,"emotion":""}

豆包语音只返回音频，没有逐字时间，所以按字符权重（标点 0.45）在句内插值，
和 edge_tts_timings.py 是同一套对齐逻辑。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parents[1]
CLIENT_DIR = AUDIO_DIR / "clients"
AIWORK = AUDIO_DIR.parents[1]
for p in (CLIENT_DIR, AIWORK / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import doubao_tts  # noqa: E402
from lib.ffmpeg import probe_duration  # noqa: E402

CUE = re.compile(r"\[\[([a-z][a-z0-9_-]*)\]\]")
PUNCT = set("，。！？；：、,.!?;:（）()「」『』“”\"'《》…—-　 ")


def strip_cues(s):
    plain, cues, pos = [], [], 0
    for m in CUE.finditer(s):
        seg = s[pos:m.start()]
        plain.append(seg)
        cues.append((m.group(1), sum(len(x) for x in plain)))
        pos = m.end()
    plain.append(s[pos:])
    return "".join(plain), cues


def char_weights(text):
    return [0.45 if ch in PUNCT else (0.0 if ch.isspace() else 1.0) for ch in text]


def main():
    src = Path(sys.argv[1])
    build = Path(sys.argv[2])
    audio = build / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    data = json.loads(src.read_text(encoding="utf-8"))
    v = data.get("voice", {})
    voice = v.get("voice", "zh_male_qingcang_uranus_bigtts")
    speed = float(v.get("speed", 1.0))
    emotion = v.get("emotion") or None
    sample_rate = int(v.get("sample_rate", 24000))

    lead, gap, breathe = 0.35, 0.22, 0.35
    cursor = lead
    beats = {}
    rows = []

    for b in data["beats"]:
        bid = b["id"]
        text, cue_list = strip_cues(b["narration"])
        mp3 = audio / f"{bid}.mp3"
        mp3.write_bytes(doubao_tts.synth(
            text, voice, speed=speed, emotion=emotion, sample_rate=sample_rate, fmt="mp3",
        ))
        dur = probe_duration(mp3)
        start, end = cursor, cursor + dur

        w = char_weights(text)
        tw = sum(w) or 1.0
        chars, cum = [], 0.0
        for i, ch in enumerate(text):
            chars.append(start + 0.06 + (cum / tw) * max(0.0, dur - 0.12))
            cum += w[i]
        cues = {}
        for name, idx in cue_list:
            cues[name] = chars[idx] if idx < len(chars) else end

        beats[bid] = {"start": round(start, 3), "end": round(end, 3),
                      "text": text, "chars": [round(x, 3) for x in chars], "cues": cues}
        rows.append((bid, dur, len(text)))
        cursor = end + gap

    total = round(cursor - gap + breathe, 3)
    timings = {"total": total, "beats": beats}
    (build / "timings.json").write_text(json.dumps(timings, ensure_ascii=False, indent=1), encoding="utf-8")

    # 拼 narration.wav：静音底 + 每拍 adelay，amix 保持原音量
    wavs = []
    for bid, _, _ in rows:
        mp3 = audio / f"{bid}.mp3"
        wav = audio / f"{bid}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
                        "-ar", "48000", "-ac", "2", str(wav)], check=True)
        wavs.append((bid, wav))

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(total)]
    for _, wav in wavs:
        cmd += ["-i", str(wav)]
    parts = []
    for i, (bid, _) in enumerate(wavs, start=1):
        ms = int(round(beats[bid]["start"] * 1000))
        parts.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(1, len(wavs) + 1))
    parts.append(f"[0:a]{mix}amix=inputs={len(wavs) + 1}:duration=first:normalize=0[out]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "[out]", "-t", str(total),
            "-ar", "48000", "-ac", "2", str(build / "narration.wav")]
    subprocess.run(cmd, check=True)

    print(f"voice={voice} speed={speed} emotion={emotion or '-'}")
    for bid, dur, n in rows:
        print(f"  {bid}  {dur:5.2f}s  {n:3d}字  {n / dur:4.2f}字/秒  cues={','.join(beats[bid]['cues'])}")
    print(f"total={total:.2f}s  -> {build / 'timings.json'}")
    print(f"narration.wav -> {build / 'narration.wav'}")


if __name__ == "__main__":
    main()
