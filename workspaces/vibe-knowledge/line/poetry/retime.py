"""把 poem.json 的出场节奏统一到固定规则（2026-11-15 定稿）。

用法（从仓库根目录）：
    python workspaces/vibe-knowledge/line/poetry/retime.py \\
        workspaces/vibe-knowledge/projects/<work>/lessons/<id>/poem.json

规则：
- 多行（>=2 行）：一行一行出，2.3 秒/行，淡入 1.0 秒
- 单行：逐字 0.4 秒/字（保留原来的 marks 比例与标点停顿）
- 场景停留：per_sec 0.5 / min 5.0 / max 8.0
- 最后一场：署名后固定停 12 秒（由 render.py 计算）
"""
import json
import shutil
import sys
from pathlib import Path

from compose import card_hold, single_card_scene

GAP = 2.3          # 行与行之间
CHAR = 0.4         # 单行逐字
AFTER = {"per_sec": 0.5, "min": 5.0, "max": 8.0}


def bodies_of(lines, quotes):
    out = []
    for i, txt in enumerate(lines):
        body = txt
        if quotes and i == 0:
            body = "「" + body
        if quotes and i == len(lines) - 1:
            body = body + "」"
        out.append(body)
    return out


def line_pacing(lines, quotes, gap=GAP):
    """一行一行出：首字立即出现，其余整行 attach，行末留 gap。"""
    bodies = bodies_of(lines, quotes)
    out = []
    for i, b in enumerate(bodies):
        out.append({"text": b[0], "char": 0})
        if len(b) > 1:
            seg = {"text": b[1:], "attach": True}
            if i < len(bodies) - 1:
                seg["pause"] = gap
            out.append(seg)
        elif i < len(bodies) - 1:
            out[-1]["pause"] = gap
    return out


def rescale_char(pacing, old_base, new_base=CHAR):
    """单行场：保留 marks 的相对快慢，只把基准字速换掉。"""
    k = new_base / float(old_base or 0.34)
    out = []
    for seg in pacing:
        seg = dict(seg)
        if seg.get("char"):
            seg["char"] = round(float(seg["char"]) * k, 4)
        out.append(seg)
    return out


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    path = Path(argv[1]).resolve()
    poem = json.loads(path.read_text(encoding="utf-8"))

    backup = path.with_name("poem.before-retime.json")
    if not backup.exists():
        shutil.copy2(path, backup)

    timing = poem.setdefault("timing", {})
    old_base = float(timing.get("char") or 0.34)
    timing["char"] = CHAR
    timing["after"] = dict(AFTER)

    for i, sc in enumerate(poem["scenes"]):
        if sc.get("cards") and len(sc["cards"]) == 1:
            sc = single_card_scene(sc)
            poem["scenes"][i] = sc
        if sc.get("cards"):
            cards = sc["cards"]
            card_fade = float(sc.get("card_fade", 1.0))
            for k, c in enumerate(cards):
                hold = card_hold(c.get("lines") or []) + 2 * card_fade
                if k == len(cards) - 1:
                    hold += 1.5
                c["seconds"] = round(hold, 2)
            sc["seconds"] = round(
                float(sc.get("card_lead", 1.2))
                + sum(float(c["seconds"]) for c in cards)
                + float(sc.get("card_tail", 0.8)),
                2,
            )
            print(f"{i + 1:02d}  cards  {len(cards)} 张  {sc['seconds']:.2f}s")
            continue

        lines = sc.get("lines") or []
        if len(lines) >= 2:
            sc["pacing"] = line_pacing(lines, bool(sc.get("quotes")))
            sc["fade"] = 1.0
            mode = "line"
        else:
            sc["pacing"] = rescale_char(sc.get("pacing") or [], old_base)
            sc.pop("fade", None)
            mode = "char"
        print(f"{i + 1:02d}  {mode:4s}  {len(lines)} 行  {sum(len(x) for x in lines):3d} 字")

    path.write_text(json.dumps(poem, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved {path}")
    print(f"备份 {backup.name}")


if __name__ == "__main__":
    main(sys.argv)
