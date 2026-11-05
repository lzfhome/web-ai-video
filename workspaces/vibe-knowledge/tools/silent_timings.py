#!/usr/bin/env python3
"""无旁白字卡时间轴：给 cine 引擎生成 timings.json + 静音 narration.wav。

用法：
  python3 tools/silent_timings.py lessons/003/narration.json lessons/003/build

narration.json：{"mode":"silent","beats":[{"id":"B01","dur":7.2,"card":"…"}, …]}
每拍先给 1.5 秒画面，再出字卡；最后一拍 B11 从开头就出字卡。
"""
import json
import sys
import wave
from pathlib import Path


def main():
    src = Path(sys.argv[1])
    build = Path(sys.argv[2])
    build.mkdir(parents=True, exist_ok=True)
    data = json.loads(src.read_text(encoding="utf-8"))
    if data.get("mode") != "silent":
        raise SystemExit("narration.json 不是 silent 模式")
    lead = 0.0
    cursor = lead
    beats = {}
    rows = []
    for b in data["beats"]:
        bid = b["id"]
        dur = float(b["dur"])
        start, end = cursor, cursor + dur
        ca = b.get("card_at")
        if ca is None:
            card_at = start if bid == "B11" else start + 0.8
        else:
            card_at = start + float(ca)
        beats[bid] = {
            "start": round(start, 3),
            "end": round(end, 3),
            "text": "",
            "chars": [],
            "cues": {"card": round(card_at, 3)},
        }
        rows.append((bid, dur, b.get("card", "")))
        cursor = end
    total = round(cursor, 3)
    (build / "timings.json").write_text(
        json.dumps({"total": total, "beats": beats}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    # 静音旁白轨：48k / 立体声 / 16bit
    frames = int(round(48000 * total))
    with wave.open(str(build / "narration.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(b"\x00\x00" * 2 * frames)
    for bid, dur, card in rows:
        print(f"  {bid}  {dur:5.2f}s  {card}")
    print(f"total={total:.2f}s  -> {build / 'timings.json'}")
    print(f"silent narration.wav -> {build / 'narration.wav'}")


if __name__ == "__main__":
    main()
