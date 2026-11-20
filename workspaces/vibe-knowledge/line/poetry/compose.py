#!/usr/bin/env python3
"""把 work.json（题材/封面/BGM/内容）合成 poem.json（引擎可直接渲染的完整参数）。

用法：
  python line/poetry/compose.py <work.json> [out.json]

work.json 只写变量；defaults.json 提供所有固定观感与时间规则。
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULTS = HERE / "defaults.json"

FEEL = {
    "firm": 1.10,
    "heavy": 1.35,
    "soft": 0.90,
    "fast": 0.80,
    "slow": 1.25,
}

CN = "零一二三四五六七八九"


def cn_num(n: int) -> str:
    if n <= 10:
        return "十" if n == 10 else CN[n]
    if n < 20:
        return "十" + CN[n % 10]
    if n < 100:
        return CN[n // 10] + "十" + (CN[n % 10] if n % 10 else "")
    return str(n)


def roman(n: int) -> str:
    vals = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def bodies_of(lines, quotes: bool):
    out = []
    for i, txt in enumerate(lines):
        body = txt
        if quotes and i == 0:
            body = "「" + body
        if quotes and i == len(lines) - 1:
            body = body + "」"
        out.append(body)
    return out


def mark_ranges(flat: str, marks):
    """按顺序把 marks 落到 flat 上；返回 (start, end, feel, pause)。"""
    spans = []
    cursor = 0
    for m in marks or []:
        text = str(m.get("text", ""))
        if not text:
            continue
        at = flat.find(text, cursor)
        if at < 0:
            raise ValueError(f"marks 对不上原文：{text!r}（从第 {cursor} 字开始找）")
        feel = m.get("feel")
        if feel is not None and feel not in FEEL:
            raise ValueError(f"未知情绪标注：{feel}（可用 {', '.join(FEEL)}）")
        spans.append((at, at + len(text), feel, float(m.get("pause", 0) or 0)))
        cursor = at + len(text)
    return spans


def punct_pause(flat: str, i: int) -> float:
    ch = flat[i]
    if ch in "，、,；;：:":
        return 0.5
    if ch in "。！？!?":
        return 1.0
    if ch == "…":
        return 0.0 if (i + 1 < len(flat) and flat[i + 1] == "…") else 1.0
    return 0.0


def generate_pacing(lines, quotes: bool, marks, base: float, line_mode: bool = False):
    bodies = bodies_of(lines, quotes)
    if line_mode and len(bodies) > 1:
        segs = []
        for i, body in enumerate(bodies):
            chars = list(body)
            if not chars:
                continue
            segs.append({"text": chars[0], "char": 0})
            if len(chars) > 1:
                segs.append({"text": "".join(chars[1:]), "attach": True})
            if i < len(bodies) - 1:
                segs[-1]["pause"] = 2.3
        return segs
    flat = "".join(bodies)
    spans = mark_ranges(flat, marks)

    factors = [1.0] * len(flat)
    extras = [0.0] * len(flat)
    for a, b, feel, pause in spans:
        f = FEEL.get(feel, 1.0)
        for k in range(a, min(b, len(flat))):
            factors[k] = f
        if pause:
            extras[min(b - 1, len(flat) - 1)] += max(0.0, min(0.6, pause))

    segs = []
    run = ""
    run_char = None

    def flush():
        nonlocal run, run_char
        if run:
            segs.append({"text": run, "char": round(run_char, 3)})
            run = ""
            run_char = None

    for i, ch in enumerate(flat):
        if ch in "「」":
            flush()
            segs.append({"text": ch, "attach": True})
            continue
        c = max(0.18, min(0.65, base * factors[i]))
        p = punct_pause(flat, i) + extras[i]
        if p <= 0:
            if run_char is not None and abs(c - run_char) > 1e-9:
                flush()
            run += ch
            run_char = c
        else:
            flush()
            segs.append({"text": ch, "char": round(c, 3), "pause": round(p, 3)})
    flush()

    joined = "".join(s["text"] for s in segs)
    if joined != flat:
        raise ValueError(f"pacing 拼接不一致：{joined!r} != {flat!r}")
    return segs


def card_hold(lines):
    text = "".join(lines)
    return round(max(3.5, len(text) * 0.20 + 1.2), 2)


def footer_of(sc: dict, i: int, name: str, author: str, publisher: str, volumes: list) -> str:
    footer = sc.get("footer")
    if footer:
        return footer
    volume = sc.get("volume") or (volumes[i] if i < len(volumes) else f"第{cn_num(i + 1)}册")
    if volume and publisher:
        return f"封面：{volume} · {publisher}"
    if volume:
        return f"封面：{volume}"
    return f"封面：{publisher}" if publisher else ""


def single_card_scene(sc: dict) -> dict:
    """单卡场景回退旧单句模式：逐字/逐行、署名延迟，不走整块淡入。"""
    card = sc["cards"][0]
    out = {k: v for k, v in sc.items() if k not in ("cards", "card_fade", "card_lead", "card_tail")}
    for key in ("lines", "type", "speaker", "credit", "source", "bio", "footer2",
                "category", "type_size", "marks", "pacing", "quotes", "narration"):
        if key in card:
            out[key] = card[key]
    return out


def check_sequence(scenes: list):
    """按全片卡片顺序检查台词/旁白，同类型连续超过 2 张时提醒。"""
    kinds = []
    for sc in scenes:
        if sc.get("cards"):
            kinds.extend("旁白" if c.get("narration") else "台词" for c in sc["cards"])
        else:
            kinds.append("旁白" if sc.get("narration") else "台词")
    start = 0
    for i in range(1, len(kinds) + 1):
        if i == len(kinds) or kinds[i] != kinds[start]:
            if i - start > 2:
                print(f"⚠ 连续 {i - start} 张{kinds[start]}（第 {start + 1}–{i} 张）；"
                      "规则最多连续 2 张，建议调整台词/旁白顺序。")
            start = i


def compose(work: dict, defaults: dict) -> dict:
    title = work.get("title") or work.get("id") or "untitled"
    scenes_in = work.get("scenes") or []
    if not scenes_in:
        raise ValueError("work.json 没有 scenes")
    covers = work.get("covers") or []
    if not covers:
        raise ValueError("work.json 没有 covers：先按 TEMPLATE 的封面流程准备，再合成")
    if len(covers) < len(scenes_in):
        raise ValueError(f"封面不足：{len(covers)} 张 / {len(scenes_in)} 场")
    if not work.get("bgm"):
        raise ValueError("work.json 没有 bgm")
    bios = work.get("bio") or []
    long_bio = sum(1 for b in bios if len(b) >= 40)
    if bios and long_bio * 2 < len(scenes_in):
        print(f"⚠ 长小传只有 {long_bio}/{len(scenes_in)} 场，规则要求至少一半 ≥40 字")

    book = work.get("book") or {}
    name = book.get("name", "")
    author = book.get("author", "")
    publisher = book.get("publisher", "")
    volumes = book.get("volumes") or []

    timing = dict(defaults["timing"])
    type_default = dict(defaults["type"])
    size_map = defaults.get("scene_type_size") or {}
    palettes = defaults.get("palettes") or ["jade"]

    scenes = []
    for i, sc in enumerate(scenes_in):
        if sc.get("cards") and len(sc["cards"]) == 1:
            sc = single_card_scene(sc)
        if sc.get("cards"):
            cards_in = sc["cards"]
            footer = footer_of(sc, i, name, author, publisher, volumes)

            cards = []
            card_cfg = defaults.get("card") or {}
            card_lead = float(card_cfg.get("lead", 1.2))
            card_tail = float(card_cfg.get("tail", 0.8))
            card_fade = float(sc.get("card_fade", card_cfg.get("fade", 1.0)))
            for j, c in enumerate(cards_in):
                lines = c.get("lines")
                if not lines:
                    raise ValueError(f"scenes[{i}].cards[{j}] 缺 lines")
                kind = c.get("type") or ("dialogue" if c.get("speaker") else "narration")
                if kind not in ("dialogue", "narration", "citation"):
                    raise ValueError(f"scenes[{i}].cards[{j}].type 非法：{kind}")
                quotes = kind == "dialogue"
                narration = kind == "narration"
                credit = c.get("speaker", "")
                source = c.get("source", "")
                if source and not (source.startswith("章名：") or re.search(
                        r"(第[一二三四五六七八九十百千零]+章|序章|楔子|引子|尾声|后记|终章)", source)):
                    raise ValueError(
                        f"scenes[{i}].cards[{j}] 的 source 必须写“章名：章名”或“第X章 章名”，"
                        f"无法确认章节时留空：{source!r}"
                    )
                bio = c.get("bio") or sc.get("bio") or (bios[i] if i < len(bios) else "")
                n_lines = len(lines)
                size = c.get("type_size") or size_map.get(str(n_lines)) or defaults["type"]["size"]
                pacing = c.get("pacing")
                if not pacing:
                    pacing = generate_pacing(lines, quotes, c.get("marks"), float(timing["char"]))
                hold = round(card_hold(lines) + 2 * card_fade, 2)
                if j == len(cards_in) - 1:
                    hold = round(hold + 1.5, 2)
                cards.append({
                    "lines": lines,
                    "type": {"size": size},
                    "credit": credit,
                    "source": source,
                    "quotes": quotes or None,
                    "narration": narration or None,
                    "pacing": pacing,
                    "footer2": c.get("footer2") or sc.get("footer2") or "",
                    "footer3": sc.get("footer3", ""),
                    "footer4": c.get("footer4") or (f"生平：{bio}" if bio else sc.get("footer4", "")),
                    "category": c.get("category", ""),
                    "seconds": hold,
                })

            total = round(card_lead + sum(c["seconds"] for c in cards) + card_tail, 2)
            scenes.append({
                "cover": sc.get("cover") or (covers[i] if i < len(covers) else None),
                "palette": sc.get("palette") or palettes[i % len(palettes)],
                "blur": sc.get("blur", 6),
                "brightness": sc.get("brightness", 0.48),
                "flip": bool(sc.get("flip", False)),
                "header": sc.get("header") or f"VOL. {roman(i + 1)}",
                "footer": footer,
                "footer2": sc.get("footer2", ""),
                "footer3": sc.get("footer3", ""),
                "footer4": sc.get("footer4", ""),
                "cards": cards,
                "card_lead": card_lead,
                "card_tail": card_tail,
                "card_fade": card_fade,
                "seconds": total,
            })
            continue

        lines = sc.get("lines")
        if not lines:
            raise ValueError(f"scenes[{i}] 缺 lines")
        kind = sc.get("type") or ("dialogue" if sc.get("speaker") else "narration")
        if kind not in ("dialogue", "narration", "citation"):
            raise ValueError(f"scenes[{i}].type 非法：{kind}")

        quotes = kind == "dialogue"
        narration = kind == "narration"
        credit = sc.get("speaker") or sc.get("credit", "")
        source = sc.get("source", "")
        if source and not (source.startswith("章名：") or re.search(
                r"(第[一二三四五六七八九十百千零]+章|序章|楔子|引子|尾声|后记|终章)", source)):
            raise ValueError(
                f"scenes[{i}] 的 source 必须写“章名：章名”或“第X章 章名”，"
                f"无法确认章节时留空：{source!r}"
            )

        footer = footer_of(sc, i, name, author, publisher, volumes)

        bio = sc.get("bio")
        if bio is None and i < len(bios):
            bio = bios[i]

        n_lines = len(lines)
        size = sc.get("type_size") or size_map.get(str(n_lines)) or defaults["type"]["size"]

        pacing = sc.get("pacing")
        if not pacing:
            pacing = generate_pacing(lines, quotes, sc.get("marks"), float(timing["char"]),
                                     line_mode=len(lines) > 1)

        scenes.append({
            "cover": sc.get("cover") or (covers[i] if i < len(covers) else None),
            "palette": sc.get("palette") or palettes[i % len(palettes)],
            "blur": sc.get("blur", 6),
            "brightness": sc.get("brightness", 0.48),
            "flip": bool(sc.get("flip", False)),
            "lines": lines,
            "type": {"size": size},
            "credit": credit,
            "source": source,
            "quotes": quotes or None,
            "narration": narration or None,
            "header": sc.get("header") or f"VOL. {roman(i + 1)}",
            "footer": footer,
            "footer2": sc.get("footer2") or (bio or ""),
            "footer3": sc.get("footer3", ""),
            "footer4": sc.get("footer4", ""),
            "pacing": pacing,
            "fade": sc.get("fade", 1.0 if len(lines) > 1 else float(timing.get("fade", 0.45))),
        })

    bgm = {**defaults["bgm"], "src": work.get("bgm", "")}
    if work.get("bgm_from") is not None:
        bgm["from"] = float(work["bgm_from"])
    if work.get("bgm_fade_in") is not None:
        bgm["fade_in"] = float(work["bgm_fade_in"])

    poem = {
        "id": work.get("id") or "work",
        "title": title,
        "font": defaults["font"],
        "type": type_default,
        "timing": timing,
        "scene_seconds": defaults["scene_seconds"],
        "transition": defaults["transition"],
        "tail": defaults["tail"],
        "gap": defaults["gap"],
        "effects": defaults["effects"],
        "book": defaults["book"],
        "bgm": bgm,
        "scenes": scenes,
    }
    check_sequence(scenes)
    return poem


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法：python compose.py <work.json> [out.json]")
    work_path = Path(sys.argv[1])
    work = json.loads(work_path.read_text(encoding="utf-8"))
    defaults = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    poem = compose(work, defaults)

    out = Path(sys.argv[2]) if len(sys.argv) > 2 else work_path.with_suffix(".poem.json")
    out.write_text(json.dumps(poem, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{len(poem['scenes'])} 场  {poem['title']}")
    for i, sc in enumerate(poem["scenes"], 1):
        if sc.get("cards"):
            n = sum(len("".join(c["lines"])) for c in sc["cards"])
            print(f"  {i:02d}  cards {len(sc['cards'])} 张  {n:3d} 字")
        else:
            n = sum(len(x["text"]) for x in sc["pacing"])
            print(f"  {i:02d}  {sc['credit'] or '(旁白)':6s}  {n:3d} 字  {len(sc['pacing']):3d} 段")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
