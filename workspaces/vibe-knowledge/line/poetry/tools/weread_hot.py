#!/usr/bin/env python3
"""查微信读书「热门划线」，按划线人数排序，帮选中心句。

用法：
  python workspaces/vibe-knowledge/line/poetry/tools/weread_hot.py "书名"
  python workspaces/vibe-knowledge/line/poetry/tools/weread_hot.py "书名" --top 30
  python workspaces/vibe-knowledge/line/poetry/tools/weread_hot.py --book-id <bookId>

只读公开页面，不登录、不写文件。
注意：平台版本可能有删改/插入推广，划线高不等于能直接引用；必须回原文核对。
"""
import argparse
import json
import re
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
BASE = "https://weread.qq.com"

# 只用于提示，不自动删：这些词多半是平台插入的手游推广
AD_HINTS = ("手游", "手机游戏", "游戏", "下载", "礼包", "新区", "充值", "上线", "好礼相送")


def get(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def search(keyword: str):
    html = get(f"{BASE}/web/search/books?keyword={quote(keyword)}")
    i = html.find('"bookInfos"')
    if i < 0:
        raise SystemExit("没找到搜索结果：微信读书可能改版，或这个词没有书。")
    seg = html[i + len('"bookInfos"'):].lstrip()
    if seg.startswith(":"):
        seg = seg[1:].lstrip()
    depth, end = 0, None
    for k, ch in enumerate(seg):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = k + 1
                break
    if end is None:
        raise SystemExit("搜索结果解析失败：bookInfos 数组没有闭合。")
    arr = json.loads(seg[:end])
    return [it.get("bookInfo") or {} for it in arr]


def pick_book(books, keyword: str):
    k = keyword.strip()
    exact = [b for b in books if (b.get("title") or "").strip() == k]
    partial = [b for b in books if k in (b.get("title") or "")]
    pool = exact or partial or books
    pool = sorted(pool, key=lambda b: b.get("newRatingCount") or 0, reverse=True)
    return pool[0], (exact or partial)


def best_marks(book_id: str, count: int):
    raw = get(f"{BASE}/web/book/bestbookmarks?bookId={book_id}&count={count}")
    data = json.loads(raw)
    # 有的书没有公开热门划线，接口直接返回 {}
    return data.get("bestBookMarks") or {"totalCount": 0, "chapters": [], "items": []}


def reading_count(reader_link: str):
    """微信读书阅读人数：书页里的 readingStat.readingCount。"""
    if not reader_link:
        return None
    try:
        h = get(reader_link)
    except Exception:
        return None
    m = re.search(r'"readingCount":(\d+)', h) or re.search(r"readingCount:(\d+)", h)
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keyword", nargs="?", help="书名")
    ap.add_argument("--book-id", help="已知 bookId，跳过搜索")
    ap.add_argument("--top", type=int, default=30, help="显示前几条，默认 30")
    ap.add_argument("--count", type=int, default=50, help="向平台请求多少条，默认 50")
    ap.add_argument("--all", action="store_true", help="列出全部搜索结果")
    a = ap.parse_args()

    if not a.keyword and not a.book_id:
        ap.error("给一个书名，或用 --book-id")

    if a.book_id:
        info = {"bookId": a.book_id, "title": a.book_id, "author": "", "newRating": None,
                "newRatingCount": None}
    else:
        books = search(a.keyword)
        if not books:
            raise SystemExit("没有搜到书。")
        if a.all:
            print("搜索结果：")
            for b in books:
                print(f"  {b.get('bookId')}  {b.get('title')}  {b.get('author')}"
                      f"  {b.get('newRating')}  {b.get('newRatingCount')} 人")
            print()
        info, exact = pick_book(books, a.keyword)
        if not exact:
            print("⚠ 没有书名完全匹配，按评价人数选了第一条；用 --all 看全部结果。\n")

    bm = best_marks(str(info["bookId"]), a.count)
    chap = {c["chapterUid"]: c.get("title", "?") for c in bm.get("chapters", [])}
    items = sorted(bm.get("items", []), key=lambda x: -(x.get("totalCount") or 0))

    rating = info.get("newRating")
    rating = f"{rating / 10:.1f}" if isinstance(rating, (int, float)) and rating else "?"
    print(f"《{info.get('title')}》 {info.get('author') or ''}")
    print(f"  微信读书 {rating} 分 / {info.get('newRatingCount') or '?'} 人评价"
          f"  ·  bookId {info['bookId']}")
    rc = reading_count(info.get("readerLink"))
    if rc:
        print(f"  阅读人数 {rc:,}")
    if not items:
        print("  这本书没有公开热门划线（接口返回空），换起点/豆瓣/贴吧。")
        return
    print(f"  热门划线 Top {min(a.top, len(items))}（按划线人数；! = 疑似平台推广，回原文核对）")
    print()
    for n, it in enumerate(items[:a.top], 1):
        txt = (it.get("markText") or "").replace("\r", " ").replace("\n", " ").strip()
        flag = "!" if any(k in txt for k in AD_HINTS) else " "
        title = chap.get(it.get("chapterUid"), "?")
        print(f"{n:02d}.{flag}[{it.get('totalCount') or 0:>3}] {title[:12]:<12} | {txt[:110]}")
    if len(items) < 10:
        print("\n提示：只拿到很少的划线，可能这本书没人划，或接口收紧了。", file=sys.stderr)


if __name__ == "__main__":
    main()
