#!/usr/bin/env python3
"""B 站视频下载：yutto 的薄封装，产物 + 封面 + meta.json。

用法（仓库根目录）：
  python cine/media/engines/bilibili.py doctor
  python cine/media/engines/bilibili.py info BV1BV4y1p7Xb
  python cine/media/engines/bilibili.py download https://www.bilibili.com/video/BV1BV4y1p7Xb/
  python cine/media/engines/bilibili.py download BV1BV4y1p7Xb -q 80 --out resources/references/bilibili/BV1BV4y1p7Xb
  python cine/media/engines/bilibili.py login
  python cine/media/engines/bilibili.py setup

约定：stdout 只输出 JSON；进度/日志走 stderr。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

ENGINE = Path(__file__).resolve()
MEDIA = ENGINE.parents[1]
AIWORK = ENGINE.parents[3]
sys.path.insert(0, str(MEDIA))
sys.path.insert(0, str(AIWORK))

from clients import yutto as yc  # noqa: E402

REFERENCES = AIWORK / "resources" / "references" / "bilibili"
API_VIEW = "https://api.bilibili.com/x/web-interface/view"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

QUALITY = {
    127: "8K",
    126: "Dolby Vision",
    125: "4K HDR",
    120: "4K",
    116: "1080P60",
    112: "1080P+",
    100: "智能修复",
    80: "1080P",
    74: "720P60",
    64: "720P",
    32: "480P",
    16: "360P",
}
MEDIA_EXT = {".mp4", ".mkv", ".mov", ".m4a", ".flac", ".mp3", ".aac"}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def emit(obj: dict, code: int = 0) -> None:
    print(json.dumps(obj, ensure_ascii=True, indent=2))
    raise SystemExit(code)


def fail(action: str, message: str, **extra) -> None:
    emit({"ok": False, "action": action, "error": message, **extra}, 1)


def http_json(url: str, params: dict | None = None, sessdata: str | None = None) -> dict:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": UA, "Referer": "https://www.bilibili.com/"}
    if sessdata:
        headers["Cookie"] = f"SESSDATA={sessdata}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def resolve_target(raw: str) -> str:
    """BV 号 / av 号 / 完整 URL / b23 短链 → 可以交给 yutto 的 URL。"""
    raw = raw.strip()
    if re.fullmatch(r"BV[0-9A-Za-z]{10}", raw):
        return f"https://www.bilibili.com/video/{raw}/"
    if re.fullmatch(r"av\d+", raw, re.I):
        return f"https://www.bilibili.com/video/{raw.lower()}/"
    if raw.startswith(("http://", "https://")):
        if "b23.tv" in urllib.parse.urlparse(raw).netloc:
            req = urllib.request.Request(raw, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.geturl()
        return raw
    return raw


def view_info(url: str, sessdata: str | None = None) -> dict | None:
    """投稿视频元数据；番剧/直播等解析不到时返回 None，不阻塞下载。"""
    bv = re.search(r"BV[0-9A-Za-z]{10}", url)
    av = re.search(r"/av(\d+)", url, re.I)
    if not (bv or av):
        return None
    params = {"bvid": bv.group(0)} if bv else {"aid": av.group(1)}
    try:
        payload = http_json(API_VIEW, params, sessdata)
    except Exception:
        return None
    if payload.get("code") != 0 or not payload.get("data"):
        return None
    d = payload["data"]
    pages = [
        {
            "page": p.get("page"),
            "cid": p.get("cid"),
            "part": p.get("part"),
            "duration": p.get("duration"),
        }
        for p in (d.get("pages") or [])
    ]
    return {
        "bvid": d.get("bvid"),
        "aid": d.get("aid"),
        "cid": d.get("cid"),
        "title": d.get("title"),
        "owner": (d.get("owner") or {}).get("name"),
        "owner_uid": (d.get("owner") or {}).get("mid"),
        "duration": d.get("duration"),
        "pubdate": d.get("pubdate"),
        "pic": d.get("pic"),
        "desc": (d.get("desc") or "")[:500],
        "pages": pages,
        "stat": {
            "view": (d.get("stat") or {}).get("view"),
            "like": (d.get("stat") or {}).get("like"),
            "danmaku": (d.get("stat") or {}).get("danmaku"),
            "reply": (d.get("stat") or {}).get("reply"),
        },
    }


def slug_for(url: str, info: dict | None) -> str:
    if info and info.get("bvid"):
        return info["bvid"]
    if info and info.get("aid"):
        return f"av{info['aid']}"
    tail = re.search(r"(BV[0-9A-Za-z]{10}|av\d+)", url, re.I)
    if tail:
        return tail.group(1)
    return "bili_" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]


def download_cover(url: str, dest: Path) -> str | None:
    if not url:
        return None
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        dest.write_bytes(data)
        return str(dest)
    except Exception:
        return None


def probe(path: Path) -> dict:
    ffprobe = yc.ffprobe_exe()
    if not ffprobe:
        return {}
    try:
        r = subprocess.run(
            [
                ffprobe, "-v", "error",
                "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate",
                "-of", "json", str(path),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        data = json.loads(r.stdout or "{}")
    except Exception:
        return {}
    out: dict = {}
    fmt = data.get("format") or {}
    if fmt.get("duration"):
        out["duration"] = round(float(fmt["duration"]), 3)
    if fmt.get("size"):
        out["size"] = int(fmt["size"])
    for s in data.get("streams") or []:
        if s.get("codec_type") == "video" and "width" not in out:
            out["width"] = s.get("width")
            out["height"] = s.get("height")
            out["vcodec"] = s.get("codec_name")
            rate = s.get("avg_frame_rate") or ""
            if "/" in rate:
                a, b = rate.split("/", 1)
                if b and b != "0":
                    out["fps"] = round(float(a) / float(b), 3)
        elif s.get("codec_type") == "audio" and "acodec" not in out:
            out["acodec"] = s.get("codec_name")
    return out


def collect_media(root: Path) -> list[dict]:
    rows = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in MEDIA_EXT:
            rows.append({"path": str(p), "name": p.name, **probe(p)})
    rows.sort(key=lambda x: x.get("size", 0), reverse=True)
    return rows


def auth_state(sessdata: str | None) -> str:
    if sessdata:
        return "sessdata"
    if yc.AUTH_FILE.exists():
        return "file"
    return "none"


def cmd_info(a) -> None:
    url = resolve_target(a.target)
    sess = a.sessdata or None
    info = view_info(url, sess)
    emit({
        "ok": True,
        "action": "info",
        "url": url,
        "auth": auth_state(sess),
        "info": info,
        "note": None if info else "未解析到投稿视频元数据（番剧/直播/短链或接口受限）",
        "default_quality": "最高可用（未登录通常 ≤480P）",
    })


def build_cmd(a, url: str, out: Path) -> list[str]:
    cmd = [
        "--no-progress",
        "--no-color",
        "-d", str(out),
    ]
    if a.quality:
        cmd += ["-q", str(a.quality)]
    if a.audio_only:
        cmd.append("--audio-only")
    if not a.danmaku:
        cmd.append("--no-danmaku")
    if not a.subtitle:
        cmd.append("--no-subtitle")
    if a.force:
        cmd.append("-w")
    if a.proxy:
        cmd += ["-x", a.proxy]
    ff = yc.ffmpeg_exe()
    if ff:
        cmd += ["--ffmpeg-path", ff]
    cmd += yc.auth_args(a.sessdata or None)
    cmd.append(url)
    return cmd


def mask_cmd(cmd: list[str]) -> list[str]:
    out, hide = [], False
    for part in cmd:
        if hide:
            out.append("SESSDATA=***" if part.startswith("SESSDATA=") else "***")
            hide = False
            continue
        out.append(part)
        if part in {"--auth", "--sessdata"}:
            hide = True
    return out


def cmd_download(a) -> None:
    url = resolve_target(a.target)
    sess = a.sessdata or None
    info = view_info(url, sess)
    slug = slug_for(url, info)
    out = Path(a.out).expanduser().resolve() if a.out else (REFERENCES / slug)

    cmd = build_cmd(a, url, out)
    if a.dry_run:
        emit({
            "ok": True,
            "action": "download",
            "dry_run": True,
            "cmd": [str(yc.yutto_exe() or "yutto"), *mask_cmd(cmd)],
            "out": str(out),
            "info": info,
        })

    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    print(f"[bilibili] {info['title'] if info else url}", file=sys.stderr)
    print(f"[bilibili] -> {out}", file=sys.stderr)
    try:
        r = yc.run(cmd, timeout=a.timeout)
    except subprocess.TimeoutExpired:
        fail("download", f"yutto 超时（{a.timeout}s）", out=str(out))
    except Exception as e:
        fail("download", str(e), out=str(out))

    if r.returncode != 0:
        tail = "\n".join((r.stderr or r.stdout or "").strip().splitlines()[-15:])
        fail("download", f"yutto 退出码 {r.returncode}", out=str(out), log=tail)

    media = collect_media(out)
    if not media:
        tail = "\n".join((r.stderr or r.stdout or "").strip().splitlines()[-15:])
        fail("download", "yutto 跑完但没有找到媒体文件", out=str(out), log=tail)

    cover = None
    if info and info.get("pic"):
        cover = download_cover(info["pic"], out / "cover.jpg")

    meta = {
        "schema": 1,
        "source": {"url": url, **(info or {})},
        "download": {
            "at": now(),
            "quality": a.quality,
            "quality_name": QUALITY.get(a.quality) if a.quality else "highest",
            "audio_only": bool(a.audio_only),
            "auth": auth_state(sess),
            "yutto": yc.version(),
            "elapsed_s": round(time.time() - started, 1),
        },
        "files": media,
        "cover": cover,
    }
    meta_path = out / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    emit({
        "ok": True,
        "action": "download",
        "out": str(out),
        "info": info,
        "auth": auth_state(sess),
        "media": media,
        "cover": cover,
        "meta": str(meta_path),
        "elapsed_s": meta["download"]["elapsed_s"],
    })


def cmd_login(a) -> None:
    if not yc.yutto_exe():
        fail("login", "还没有安装 yutto，先跑 setup")
    yc.AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(yc.yutto_exe()), "auth", "login",
        "--mode", a.mode,
        "--timeout", str(a.timeout),
        "--auth-file", str(yc.AUTH_FILE),
    ]
    print("$", " ".join(cmd), file=sys.stderr)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        fail("login", f"登录失败/超时（退出码 {r.returncode}）", auth_file=str(yc.AUTH_FILE))
    st = yc.run(["auth", "status", "--auth-file", str(yc.AUTH_FILE)], timeout=60)
    emit({
        "ok": True,
        "action": "login",
        "auth_file": str(yc.AUTH_FILE),
        "status": (st.stdout or st.stderr).strip(),
    })


def cmd_status(_a) -> None:
    if not yc.yutto_exe():
        fail("status", "还没有安装 yutto，先跑 setup")
    if not yc.AUTH_FILE.exists():
        emit({"ok": True, "action": "status", "logged_in": False, "auth_file": str(yc.AUTH_FILE)})
    r = yc.run(["auth", "status", "--auth-file", str(yc.AUTH_FILE)], timeout=60)
    text = (r.stdout or r.stderr).strip()
    emit({
        "ok": r.returncode == 0,
        "action": "status",
        "logged_in": r.returncode == 0,
        "auth_file": str(yc.AUTH_FILE),
        "status": text,
    }, 0 if r.returncode == 0 else 1)


def cmd_setup(_a) -> None:
    try:
        res = yc.setup()
    except Exception as e:
        fail("setup", str(e))
    emit({"ok": True, "action": "setup", **res, "ffmpeg": yc.ffmpeg_exe()})


def cmd_doctor(_a) -> None:
    checks = {
        "yutto": yc.version(),
        "yutto_exe": str(yc.yutto_exe()) if yc.yutto_exe() else None,
        "ffmpeg": yc.ffmpeg_exe(),
        "ffprobe": yc.ffprobe_exe(),
        "auth_file": str(yc.AUTH_FILE),
        "logged_in": yc.AUTH_FILE.exists(),
    }
    ok = bool(checks["yutto"] and checks["ffmpeg"])
    emit({"ok": ok, "action": "doctor", **checks})


def main() -> None:
    ap = argparse.ArgumentParser(description="B 站视频下载（yutto）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info", help="只看元数据")
    p.add_argument("target", help="URL / BV / av")
    p.add_argument("--sessdata", default=None)
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("download", help="下载视频/音频")
    p.add_argument("target", help="URL / BV / av")
    p.add_argument("--out", default=None, help="默认 resources/references/bilibili/<BV>")
    p.add_argument("-q", "--quality", type=int, choices=sorted(QUALITY), default=None,
                   help="默认最高可用；未登录通常只有 480P")
    p.add_argument("--audio-only", action="store_true")
    p.add_argument("--danmaku", action="store_true", help="同时保存弹幕（默认不存）")
    p.add_argument("--subtitle", action="store_true", help="同时保存字幕（需要登录）")
    p.add_argument("--force", action="store_true", help="覆盖已下载内容")
    p.add_argument("--sessdata", default=None, help="也可用环境变量 BILIBILI_SESSDATA")
    p.add_argument("--proxy", default=None, help="如 http://172.16.11.83:1087")
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("login", help="扫码登录，凭证写到 tools/local/yutto-auth.toml")
    p.add_argument("--mode", choices=["web", "terminal"], default="web")
    p.add_argument("--timeout", type=int, default=180)
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("status", help="看登录态")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("setup", help="创建 tools/local/venv-yutto 并装 yutto")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("doctor", help="检查 yutto / ffmpeg / 登录态")
    p.set_defaults(func=cmd_doctor)

    a = ap.parse_args()
    if getattr(a, "sessdata", None) is None:
        a.sessdata = __import__("os").environ.get("BILIBILI_SESSDATA")
    a.func(a)


if __name__ == "__main__":
    main()
