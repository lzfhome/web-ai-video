#!/usr/bin/env python3
"""产线 poetry-tts：书封 + 诗句 + 真配音（豆包语音 Seed-TTS 2.0）。

和 poetry 的区别：场景时长不再固定，而是「前奏 + 配音长度 + 留白」；
文字由配音的时长决定什么时候出，第 N 行跟着声音往后排。

流程：
  poem.json（含 voice / say）
    → 逐场合成 build/audio/scXX.mp3
    → 回写 poem.json 的 seconds / gap
    → 拼 build/narration.wav + build/timings.json
    → 交给 dom-narrated 渲染（timings 已存在，不会重算）

用法：
  python project.py build poetry-tts
  CINE_ROOT=... python line/poetry-tts/render.py <lesson> --workers 2 --force
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[4]
ROOT = Path(os.environ.get("CINE_ROOT") or Path.cwd()).expanduser().resolve()
CINE = AIWORK / "cine"
DOM = AIWORK / "workspaces/vibe-knowledge/line/dom-narrated/render.py"

sys.path.insert(0, str(CINE / "audio" / "clients"))
sys.path.insert(0, str(AIWORK / "tools"))

import doubao_tts  # noqa: E402
from lib.ffmpeg import FFMPEG, probe_duration  # noqa: E402

DEFAULT_VOICE = {
    "engine": "doubao",
    "voice": "zh_male_qingcang_uranus_bigtts",
    "speed": 0.9,
}
DEFAULT_SAY = {"pre": 0.6, "lead": 0.5, "post": 1.4}


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def scene_text(sc: dict) -> str:
    if sc.get("say"):
        return str(sc["say"]).strip()
    lines = sc.get("lines") or [sc.get("line1", ""), sc.get("line2", "")]
    return "".join(x for x in lines if x).strip()


def synth_scene(text: str, vcfg: dict, out: Path, force: bool) -> float:
    meta_path = out.with_suffix(".json")
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    want = {"text": text, "voice": vcfg.get("voice"), "speed": float(vcfg.get("speed", 1.0))}
    if (not force) and out.exists() and meta.get("want") == want:
        return probe_duration(out)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(doubao_tts.synth(
        text,
        want["voice"],
        speed=want["speed"],
        emotion=vcfg.get("emotion") or None,
        sample_rate=int(vcfg.get("sample_rate", 24000)),
        fmt="mp3",
    ))
    dur = probe_duration(out)
    meta_path.write_text(json.dumps({"want": want, "dur": round(dur, 3)}, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    return dur


def make_narration(build: Path, plan: list, total: float):
    """静音底 + 每场 adelay，拼成 narration.wav。"""
    audio_dir = build / "audio"
    wavs = []
    for _, sc_no, _, _, wav_path in plan:
        wav = audio_dir / f"sc{sc_no:02d}.wav"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(wav_path),
                        "-ar", "48000", "-ac", "2", str(wav)], check=True)
        wavs.append((sc_no, wav))

    cmd = [FFMPEG, "-y", "-loglevel", "error",
           "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{total:.3f}"]
    for _, wav in wavs:
        cmd += ["-i", str(wav)]
    parts = []
    for i, (_, _, start, _, _) in enumerate(plan, start=1):
        ms = int(round(start * 1000))
        parts.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(1, len(wavs) + 1))
    parts.append(f"[0:a]{mix}amix=inputs={len(wavs) + 1}:duration=first:normalize=0[out]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "[out]",
            "-t", f"{total:.3f}", "-ar", "48000", "-ac", "2", str(build / "narration.wav")]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lesson")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--port", default="8964")
    ap.add_argument("--force", action="store_true", help="忽略缓存，重新合成全部配音")
    args = ap.parse_args()

    lesson_dir = ROOT / "lessons" / args.lesson
    build = lesson_dir / "build"
    build.mkdir(parents=True, exist_ok=True)
    poem_path = lesson_dir / "poem.json"
    if not poem_path.exists():
        raise SystemExit(f"缺少参数文件：{poem_path}")

    poem = json.loads(poem_path.read_text(encoding="utf-8"))
    scenes = poem.get("scenes") or []
    if not scenes:
        raise SystemExit("poem.json 里没有 scenes")

    vcfg = {**DEFAULT_VOICE, **(poem.get("voice") or {})}
    say = {**DEFAULT_SAY, **(poem.get("say") or {})}
    pre, lead, post = float(say["pre"]), float(say["lead"]), float(say["post"])

    audio = build / "audio"
    audio.mkdir(parents=True, exist_ok=True)

    cursor = 0.0
    plan = []
    rows = []
    for i, sc in enumerate(scenes, start=1):
        text = scene_text(sc)
        if not text:
            raise SystemExit(f"scenes[{i - 1}] 没有可读文字（lines / say 都为空）")
        mp3 = audio / f"sc{i:02d}.mp3"
        scfg = {**vcfg, **(sc.get("voice") or {})}
        dur = synth_scene(text, scfg, mp3, args.force)

        sec = round(pre + lead + dur + post, 3)
        start = round(cursor + pre + lead, 3)
        line_count = len([x for x in (sc.get("lines") or [sc.get("line1", "")]) if x])
        step = clamp(dur * 0.62 / max(1, line_count - 1), 0.45, 1.9) if line_count > 1 else 0.28

        sc["seconds"] = sec
        gap = dict(sc.get("gap") or {})
        gap.update({
            "image_in": pre,
            "text1": round(pre + lead, 3),
            "credit": round(pre + lead + 0.2, 3),
            "line_step": round(step, 3),
        })
        sc["gap"] = gap

        plan.append((i, i, start, dur, mp3))
        rows.append((i, dur, sec, start, len(text), text[:18]))
        cursor = round(cursor + sec, 3)

    total = cursor
    poem_path.write_text(json.dumps(poem, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    make_narration(build, plan, total)

    beats = {}
    for (i, _, start, dur, _), row in zip(plan, rows):
        beats[f"B{i:02d}"] = {
            "start": start,
            "end": round(start + dur, 3),
            "text": scene_text(scenes[i - 1]),
            "chars": [],
            "cues": {},
        }
    (build / "timings.json").write_text(
        json.dumps({"total": total, "beats": beats}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    print(f"voice={vcfg.get('voice')} speed={vcfg.get('speed')}")
    for i, dur, sec, start, n, sample in rows:
        print(f"  B{i:02d}  配音 {dur:5.2f}s  本场 {sec:5.2f}s  起 {start:6.2f}s  {n:3d}字  {sample}…")
    print(f"total={total:.2f}s  -> {build / 'timings.json'}")
    print(f"narration.wav -> {build / 'narration.wav'}")

    env = {**os.environ, "CINE_ROOT": str(ROOT)}
    cmd = [sys.executable, str(DOM), args.lesson, "--workers", str(args.workers),
           "--port", str(args.port), "--shot", "jpeg", "--encoder", "x264"]
    print("poetry-tts → dom-narrated")
    print("$", " ".join(cmd[1:]))
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    main()
