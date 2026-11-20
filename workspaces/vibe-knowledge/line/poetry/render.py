#!/usr/bin/env python3
"""产线 poetry：书封决定背景 + 代码诗句排版 + BGM。

参数只有一份：lessons/<lesson>/poem.json。
本脚本先按 poem.json 的 scenes 生成 narration.json / timings.json（静音时间轴），
再交给 dom-narrated 渲染；所以场景时长和成片时长永远一致，不用手改两处。
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

sys.path.insert(0, str(AIWORK))
from tools.lib.ffmpeg import probe_duration  # noqa: E402


def check_bgm(lesson_dir: Path, build: Path, data: dict):
    """BGM 短于成片时提前警告，不要等交付后才发现结尾没声音。"""
    src = (data.get("bgm") or {}).get("src")
    if not src:
        return
    p = Path(src)
    if not p.is_absolute():
        p = lesson_dir / "assets" / src
    if not p.exists():
        return
    try:
        total = float(json.loads((build / "timings.json").read_text(encoding="utf-8"))["total"])
        dur = probe_duration(p)
    except Exception:
        return
    if dur + 0.01 < total:
        print(f"⚠ BGM 只有 {dur:.1f}s，成片 {total:.1f}s：结尾约 {total - dur:.1f}s 会静音")


def check_poem(data: dict, lesson_dir: Path):
    """poem.json 的基本校验：错误在渲染前说出来，而不是等浏览器报 JS 错。"""
    problems = []
    scenes = data.get("scenes") or []
    if not scenes:
        problems.append("scenes 不能为空")
    for i, sc in enumerate(scenes):
        tag = f"scenes[{i}]"
        if not sc.get("cover"):
            problems.append(f"{tag}.cover 必填")
        elif not (lesson_dir / "assets" / sc["cover"]).exists():
            problems.append(f"{tag}.cover 找不到文件：assets/{sc['cover']}")
        if not (sc.get("line1") or sc.get("lines") or sc.get("cards")):
            problems.append(f"{tag}.line1、lines 或 cards 必填")
        for j, card in enumerate(sc.get("cards") or []):
            if not card.get("lines"):
                problems.append(f"{tag}.cards[{j}].lines 必填")
            # source 允许留空：章节无法确认时，只保留册名/册号。
        try:
            if not 0 <= float(sc.get("blur", 7)) <= 40:
                problems.append(f"{tag}.blur 需要在 0–40 之间")
        except (TypeError, ValueError):
            problems.append(f"{tag}.blur 不是数字")
    bgm = data.get("bgm") or {}
    if bgm.get("src") and not (lesson_dir / "assets" / bgm["src"]).exists():
        problems.append(f"bgm 找不到文件：assets/{bgm['src']}")
    if problems:
        raise SystemExit("poem.json 有问题：\n  - " + "\n  - ".join(problems))


def _bodies(sc: dict):
    lines = [x for x in (sc.get("lines") or [sc.get("line1"), sc.get("line2")]) if x]
    quoted = bool(sc.get("quotes"))
    out = []
    for i, txt in enumerate(lines):
        body = txt
        if quoted and i == 0:
            body = "「" + body
        if quoted and i == len(lines) - 1:
            body = body + "」"
        out.append(body)
    return out


def _text_dur(sc: dict, timing: dict) -> float:
    """跟 poetry.js 的 sceneSchedule 同一套：有 pacing 按情绪脚本，没有就匀速。"""
    base = float(timing.get("char", 0.1))
    flat = "".join(_bodies(sc))
    pace = sc.get("pacing")
    if pace:
        idx, t, ok = 0, 0.0, True
        for seg in pace:
            text = str(seg.get("text", ""))
            if not text or flat[idx:idx + len(text)] != text:
                ok = False
                break
            if not seg.get("attach"):
                t += float(seg.get("char", base)) * len(text)
            t += float(seg.get("pause", 0))
            idx += len(text)
        if ok and idx == len(flat):
            return t
    return base * len(flat)


def _last_at(sc: dict, timing: dict) -> float:
    """最后一个字（含贴附的闭引号）的出现时刻。"""
    base = float(timing.get("char", 0.1))
    flat = "".join(_bodies(sc))
    pace = sc.get("pacing")
    if pace:
        idx, t, prev, last, ok = 0, 0.0, 0.0, 0.0, True
        for seg in pace:
            text = str(seg.get("text", ""))
            if not text or flat[idx:idx + len(text)] != text:
                ok = False
                break
            c = float(seg.get("char", base))
            for _ in text:
                if seg.get("attach"):
                    last = prev
                else:
                    last = t
                    prev = t
                    t += c
            t += float(seg.get("pause", 0))
            idx += len(text)
        if ok and idx == len(flat):
            return last
    return base * max(0, len(flat) - 1)


def sync_poem(lesson_dir: Path, build: Path, env: dict):
    """poem.json → narration.json → timings.json / narration.wav"""
    poem = lesson_dir / "poem.json"
    if not poem.exists():
        raise SystemExit(f"缺少参数文件：{poem}")
    data = json.loads(poem.read_text(encoding="utf-8"))
    check_poem(data, lesson_dir)
    scenes = data.get("scenes") or []
    if not scenes:
        raise SystemExit("poem.json 里没有 scenes")

    base = float(data.get("scene_seconds", 15))
    timing = data.get("timing")
    beats = []
    for i, sc in enumerate(scenes):
        if sc.get("seconds") is not None:
            dur = float(sc["seconds"])
        elif timing:
            # 和 poetry.js 的 TIMING 保持同一套公式：lead + 字数×char + 署名停留 + 收尾
            t = {"lead": 1.2, "char": 0.1, "credit_hold": 2.4, "tail": 0.8,
                 "after": 0, "min": 4, "max": 14}
            t.update({k: v for k, v in timing.items() if v is not None})
            lead = float((sc.get("gap") or {}).get("text1")
                         or (data.get("gap") or {}).get("text1") or t["lead"])
            td = _text_dur(sc, t)
            a = t.get("after", 0)
            credit_fade = float((data.get("gap") or {}).get("credit_dur", 0.95))
            if isinstance(a, dict):
                hold = max(float(a.get("min", 0.5)),
                           min(float(a.get("max", 4.0)),
                               td * float(a.get("per_sec", 0.25))))
                dur = lead + _last_at(sc, t) + 2.0 + credit_fade + hold
            else:
                dur = (lead + td + float(t["credit_hold"])
                       + float(t["tail"]) + float(a or 0))
            if i == len(scenes) - 1:
                # 最后一场固定停 12 秒，不受字数与 max 限制
                dur = lead + _last_at(sc, t) + 2.0 + credit_fade + 12.0
            else:
                dur = max(float(t["min"]), min(float(t["max"]), dur))
        else:
            dur = float(sc.get("seconds", base))
        first = (sc.get("cards") or [{}])[0]
        label = sc.get("line1") or ((first.get("lines") or [""])[0])
        beats.append({
            "id": f"B{i + 1:02d}",
            "dur": round(dur, 3),
            "card": (label or "")[:12],
        })

    narration = lesson_dir / "narration.json"
    narration.write_text(
        json.dumps({"mode": "silent", "beats": beats}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, str(CINE / "audio/engines/tts_silent.py"), str(narration), str(build)],
        cwd=ROOT, env=env, check=True,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lesson")
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--shot", default="jpeg", choices=["jpeg", "png"])
    ap.add_argument("--tts", default="auto", choices=["auto", "edge"])
    ap.add_argument("--port", default="8964")
    ap.add_argument("--encoder", default="x264", choices=["x264", "nvenc"])
    ap.add_argument("--from", dest="t0", default=None)
    ap.add_argument("--to", dest="t1", default=None)
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--keep-narration", action="store_true",
                    help="不从 poem.json 重建时间轴（给需要真人/配音的版本用）")
    args = ap.parse_args()

    lesson_dir = ROOT / "lessons" / args.lesson
    build = lesson_dir / "build"
    build.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "CINE_ROOT": str(ROOT)}
    if not args.keep_narration:
        sync_poem(lesson_dir, build, env)

    poem_data = json.loads((lesson_dir / "poem.json").read_text(encoding="utf-8"))
    check_bgm(lesson_dir, build, poem_data)

    cmd = [sys.executable, str(DOM), args.lesson, "--port", args.port,
           "--workers", str(args.workers), "--shot", args.shot,
           "--tts", args.tts, "--encoder", args.encoder]
    if args.fps:
        cmd += ["--fps", str(args.fps)]
    if args.t0 is not None:
        cmd += ["--from", args.t0]
    if args.t1 is not None:
        cmd += ["--to", args.t1]
    if args.audio_only:
        cmd.append("--audio-only")
    print("poetry → dom-narrated")
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    main()
