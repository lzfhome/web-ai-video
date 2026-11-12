#!/usr/bin/env python3
"""豆包语音合成（Seed-TTS 2.0 / 声音复刻）客户端，给 cine 的产线共用。

接口：https://openspeech.bytedance.com/api/v3/tts/unidirectional
鉴权：X-Api-Key —— 豆包语音控制台的 API Key（UUID 形态），
      不是方舟的 ark- 开头的 key，两者不通用。

key 的找法（按顺序）：
  1. 函数参数 key=...
  2. 环境变量 DOUBAO_TTS_API_KEY / TTS_API_KEY
  3. ~/.config/aiwork/tts.env 里的 DOUBAO_TTS_API_KEY=...

命令行：
  python cine/audio/clients/doubao_tts.py --text "天地不仁" --voice zh_male_qingcang_uranus_bigtts --out a.mp3
  python cine/audio/clients/doubao_tts.py --list
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

API_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
RESOURCE_TTS = "seed-tts-2.0"
RESOURCE_ICL = "seed-icl-2.0"

ENV_NAMES = ("DOUBAO_TTS_API_KEY", "TTS_API_KEY")
ENV_FILE = Path.home() / ".config" / "aiwork" / "tts.env"
# 和 video-studio 共用同一把 key：那边写在 config.secrets.json 的 tts_api_key
STUDIO_SECRETS = Path(__file__).resolve().parents[3] / "tools" / "video-studio" / "config.secrets.json"

# 常用音色：id -> (中文名, 性别)。完整 370 个在
# https://www.volcengine.com/docs/6561/1257544
VOICES = {
    "zh_male_qingcang_uranus_bigtts": ("清苍", "男"),
    "zh_male_ruyayichen_uranus_bigtts": ("儒雅逸尘", "男"),
    "zh_male_yizhipiannan_uranus_bigtts": ("一纸翩男", "男"),
    "zh_male_silang_uranus_bigtts": ("四郎", "男"),
    "zh_male_taocheng_uranus_bigtts": ("陶成", "男"),
    "zh_male_liufei_uranus_bigtts": ("刘飞", "男"),
    "zh_male_dayi_uranus_bigtts": ("大义", "男"),
    "zh_male_ruyaqingnian_uranus_bigtts": ("儒雅青年", "男"),
    "zh_male_shaonianzixin_uranus_bigtts": ("少年自信", "男"),
    "zh_female_vv_uranus_bigtts": ("VV", "女"),
    "zh_female_xiaohe_uranus_bigtts": ("小何", "女"),
    "zh_female_tianmeixiaoyuan_uranus_bigtts": ("甜美校园", "女"),
    "zh_female_wenroumama_uranus_bigtts": ("温柔妈妈", "女"),
    "zh_female_qingxinnvsheng_uranus_bigtts": ("清新女生", "女"),
}


def api_key(explicit: str | None = None) -> str:
    """按 参数 → 环境变量 → ~/.config/aiwork/tts.env 的顺序找 key。"""
    if explicit:
        return explicit.strip()
    for name in ENV_NAMES:
        v = os.environ.get(name)
        if v:
            return v.strip()
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in ENV_NAMES:
                return v.strip().strip('"').strip("'")
    if STUDIO_SECRETS.exists():
        try:
            data = json.loads(STUDIO_SECRETS.read_text(encoding="utf-8-sig"))
            v = (data.get("tts_api_key") or "").strip()
            if v:
                return v
        except (OSError, json.JSONDecodeError):
            pass
    raise RuntimeError(
        "找不到豆包语音 API Key：设 DOUBAO_TTS_API_KEY 环境变量，"
        f"或写到 {ENV_FILE}，或在 video-studio/config.secrets.json 里填 tts_api_key"
    )


def _decode_stream(raw: bytes) -> tuple[bytes, list[str]]:
    """响应是若干 JSON 对象连在一起，data 字段是 base64 音频。"""
    text = raw.decode("utf-8", "replace").strip()
    dec = json.JSONDecoder()
    i, chunks, errors = 0, [], []
    while i < len(text):
        while i < len(text) and text[i] in " \r\n\t":
            i += 1
        if i >= len(text):
            break
        try:
            obj, i = dec.raw_decode(text, i)
        except json.JSONDecodeError:
            break
        code = obj.get("code")
        if code not in (0, None):
            errors.append(f"{code}: {obj.get('message')}")
        data = obj.get("data")
        if data:
            chunks.append(base64.b64decode(data))
    return b"".join(chunks), errors


def synth(
    text: str,
    voice: str,
    *,
    speed: float = 1.0,
    speech_rate: int | None = None,
    loudness_rate: int | None = None,
    emotion: str | None = None,
    emotion_scale: float | None = None,
    context_texts: list[str] | None = None,
    section_id: str | None = None,
    sample_rate: int = 24000,
    fmt: str = "mp3",
    resource_id: str = RESOURCE_TTS,
    model: str | None = None,
    key: str | None = None,
    uid: str = "aiwork",
    timeout: int = 120,
) -> bytes:
    """合成一段文字，返回音频字节。失败抛 RuntimeError。

    speed 只是便利写法：0.9 = 慢 10%，会换算成 V3 的 speech_rate（-50..100）。
    想精确控制就直接给 speech_rate。
    """
    text = (text or "").strip()
    if not text:
        raise RuntimeError("合成文本为空")

    audio_params = {"format": fmt, "sample_rate": int(sample_rate)}
    if speech_rate is None and speed and float(speed) != 1.0:
        speech_rate = int(round((float(speed) - 1.0) * 100))
    if speech_rate:
        audio_params["speech_rate"] = max(-50, min(100, int(speech_rate)))
    if loudness_rate:
        audio_params["loudness_rate"] = max(-50, min(100, int(loudness_rate)))
    if emotion:
        audio_params["emotion"] = emotion
    if emotion_scale is not None:
        audio_params["emotion_scale"] = float(emotion_scale)

    req_params = {
        "text": text,
        "speaker": voice,
        "audio_params": audio_params,
    }
    if model:
        # seed-tts-2.0-standard / seed-tts-2.0-expressive（后者仅声音复刻 2.0）
        req_params["model"] = model

    additions = {}
    if context_texts:
        # 语音指令：自然语言描述怎么念，只取第一条，不计费
        additions["context_texts"] = [str(context_texts[0])]
    if section_id:
        additions["section_id"] = section_id
    if additions:
        # additions 是 JSON 字符串，不是对象（服务端按 string 解析）
        req_params["additions"] = json.dumps(additions, ensure_ascii=False)

    payload = {"user": {"uid": uid}, "req_params": req_params}

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "X-Api-Key": api_key(key),
            "X-Api-Resource-Id": resource_id,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read()[:400].decode("utf-8", "replace")
        raise RuntimeError(f"豆包语音 HTTP {e.code}: {detail}") from e

    audio, errors = _decode_stream(raw)
    if not audio:
        raise RuntimeError("豆包语音没有返回音频：" + ("; ".join(errors[:3]) or "空响应"))
    return audio


def synth_to_file(text: str, voice: str, out: str | Path, **kwargs) -> Path:
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(synth(text, voice, **kwargs))
    return p


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="豆包语音合成")
    ap.add_argument("--text", help="要合成的文字")
    ap.add_argument("--voice", default="zh_male_qingcang_uranus_bigtts")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--emotion", default=None)
    ap.add_argument("--sample-rate", type=int, default=24000, choices=[8000, 16000, 24000])
    ap.add_argument("--format", default="mp3", choices=["mp3", "wav", "pcm", "ogg_opus"])
    ap.add_argument("--out", default="tts.mp3")
    ap.add_argument("--key", default=None, help="临时指定 key（默认读环境变量/tts.env）")
    ap.add_argument("--list", action="store_true", help="列出常用音色")
    args = ap.parse_args(argv)

    if args.list:
        for vid, (name, gender) in VOICES.items():
            print(f"{gender}  {vid:42} {name}")
        return 0
    if not args.text:
        ap.error("需要 --text，或加 --list 看音色")

    out = synth_to_file(
        args.text, args.voice, args.out,
        speed=args.speed, emotion=args.emotion,
        sample_rate=args.sample_rate, fmt=args.format, key=args.key,
    )
    print(f"{out}  {out.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
