#!/usr/bin/env python3
"""本地增强层：火山方舟 Seedance（视频）/ Seedream（图片）。

CLI 和文件落盘在这里；鉴权、请求、轮询、下载在 `cine/image/lib/ark_client.py`。

用法（建议用 CINE_PY，因为 --frames 要 numpy）：
  # 先看计划，不花钱
  python cine/image/engines/ark.py image --prompt "..." --out lessons/003/assets/img/a01.jpg
  python cine/image/engines/ark.py video --prompt "..." --out lessons/003/assets/clips/v01.mp4
  python cine/image/engines/ark.py video --prompt "..." --first-frame assets/img/a01.jpg --duration 4 --resolution 480p --out .../v01.mp4 --frames

  # 确认后才真正提交
  python cine/image/engines/ark.py image ... --yes
  python cine/image/engines/ark.py video ... --yes

  # 批量：assets.json 里 items[]，每条 kind=image/video
  python cine/image/engines/ark.py assets lessons/003/assets_ark.json --yes

默认只 dry-run，不加 --yes 不提交，符合 Skill「先确认后生成」。
视频默认 generate_audio=false；要环境声加 --generate-audio。
"""
import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(AIWORK))
from cine.image.lib import ark_client as ark  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SKILL = AIWORK / "skills/vibe-knowledge"
DEFAULT_VIDEO = ark.DEFAULT_VIDEO
DEFAULT_IMAGE = ark.DEFAULT_IMAGE


def plan(title, payload, out, yes=False):
    print(f"\n== {title} ==")
    print(json.dumps({k: v for k, v in payload.items() if k != "content"}, ensure_ascii=False, indent=1))
    if "content" in payload:
        print("content:", json.dumps(payload["content"], ensure_ascii=False)[:600])
    print("out:", out)
    print("（--yes：已提交）" if yes else "（dry-run：未提交；确认后加 --yes）")
    print()


def gen_image(args):
    out = Path(args.out)
    payload = {
        "model": args.model or DEFAULT_IMAGE,
        "prompt": args.prompt,
        "size": args.size,
        "response_format": "b64_json",
        "watermark": False,
    }
    if args.reference:
        payload["image"] = [ark.data_url(Path(p)) if Path(p).exists() else p for p in args.reference]
    plan("Seedream 图片", payload, out, yes=args.yes)
    if not args.yes:
        return
    items = ark.generate_images(payload)
    out.parent.mkdir(parents=True, exist_ok=True)
    made = []
    for i, item in enumerate(items):
        b64 = item.get("b64_json")
        if not b64:
            continue
        of = str(item.get("output_format") or "").lower().lstrip(".")
        ext = {"jpeg": ".jpg", "jpg": ".jpg", "png": ".png", "webp": ".webp"}.get(of, out.suffix or ".png")
        p = out if len(items) == 1 else out.with_name(f"{out.stem}_{i + 1}{ext}")
        p.write_bytes(base64.b64decode(b64))
        made.append(p)
    for p in made:
        print("→", p)
    if not made:
        sys.exit("没有拿到图片数据")


def gen_video(args):
    out = Path(args.out)
    model = args.model or DEFAULT_VIDEO
    allowed_res = {
        "doubao-seedance-2-5-flash-261115": {"480p", "720p"},
        "doubao-seedance-2-0-mini-260615": {"480p", "720p"},
        "doubao-seedance-2-0-fast-260128": {"480p", "720p"},
    }.get(model)
    if allowed_res and args.resolution not in allowed_res:
        sys.exit(f"{model} 不支持 {args.resolution}；可选：{', '.join(sorted(allowed_res))}")

    content = [{"type": "text", "text": args.prompt}]
    if args.first_frame and args.reference:
        sys.exit("首帧图和参考图不能同时传：Seedance 的首帧/首尾帧与全模态参考是互斥场景")
    if args.last_frame and args.reference:
        sys.exit("尾帧图和参考图不能同时传：Seedance 的首帧/首尾帧与全模态参考是互斥场景")
    if args.first_frame:
        fp = Path(args.first_frame)
        if args.yes and not fp.exists():
            sys.exit(f"首帧不存在：{fp}")
        url = ark.data_url(fp) if (args.yes and fp.exists()) else f"<file:{fp}>"
        content.append({"type": "image_url", "image_url": {"url": url}, "role": "first_frame"})
    if args.last_frame:
        if not args.first_frame:
            sys.exit("首尾帧模式需要同时给 --first-frame 和 --last-frame")
        lp = Path(args.last_frame)
        if args.yes and not lp.exists():
            sys.exit(f"尾帧不存在：{lp}")
        url = ark.data_url(lp) if (args.yes and lp.exists()) else f"<file:{lp}>"
        content.append({"type": "image_url", "image_url": {"url": url}, "role": "last_frame"})
    for ref in args.reference or []:
        rp = Path(ref)
        if args.yes and not rp.exists():
            sys.exit(f"参考图不存在：{rp}")
        url = ark.data_url(rp) if (args.yes and rp.exists()) else f"<file:{rp}>"
        content.append({"type": "image_url", "image_url": {"url": url}, "role": "reference_image"})
    # Seedance 2.5 系列的首帧/首尾帧任务只支持 ratio=adaptive
    ratio = "adaptive" if ((args.first_frame or args.last_frame) and model.startswith("doubao-seedance-2-5")) else args.ratio
    payload = {
        "model": model,
        "content": content,
        "resolution": args.resolution,
        "ratio": ratio,
        "duration": args.duration,
        "seed": args.seed,
        "camera_fixed": bool(args.camera_fixed),
        "watermark": False,
        "generate_audio": bool(args.generate_audio),
    }
    # 该参数只属于 Seedance 2.5 的全模态参考；首帧/首尾帧和文生视频传了会 400
    if args.reference and not args.first_frame and not args.last_frame and model.startswith("doubao-seedance-2-5"):
        payload["omni_reference_task_type"] = "auto"
    plan("Seedance 视频", payload, out, yes=args.yes)
    if not args.yes:
        return
    tid = ark.create_video_task(payload)
    print("task_id:", tid)
    info = ark.wait_video_task(tid, poll=args.poll, timeout=args.timeout)
    ark.download(ark.video_url(info), out)
    print("→", out)
    if args.frames:
        frames_dir = out.with_suffix("")
        cmd = [sys.executable, str(SKILL / "tools/clip2frames.py"), str(out), str(frames_dir), "--fps", str(args.fps)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            print(r.stderr[-800:], file=sys.stderr)
            sys.exit("clip2frames 失败")
        n = (r.stdout or "").strip().splitlines()[-1] if r.stdout.strip() else "?"
        print(f"frames → {frames_dir}  n={n}")


def run_assets(args):
    src = Path(args.file)
    data = json.loads(src.read_text(encoding="utf-8"))
    base = src.parent
    items = data.get("items") or []
    if not items:
        sys.exit("assets.json 里没有 items")
    for item in items:
        ns = argparse.Namespace(**vars(args))
        for k, v in item.items():
            setattr(ns, k, v)
        ns.out = str(base / item["out"]) if not Path(item["out"]).is_absolute() else item["out"]
        if item.get("first_frame") and not Path(item["first_frame"]).is_absolute():
            ns.first_frame = str(base / item["first_frame"])
        if item.get("last_frame") and not Path(item["last_frame"]).is_absolute():
            ns.last_frame = str(base / item["last_frame"])
        if item.get("reference"):
            ns.reference = [str(base / r) if not Path(r).is_absolute() else r for r in item["reference"]]
        if item.get("kind") == "image":
            gen_image(ns)
        elif item.get("kind") == "video":
            gen_video(ns)
        else:
            sys.exit(f"未知 kind：{item.get('kind')}")
        if not args.yes:
            continue


def main():
    ap = argparse.ArgumentParser(description="Seedance/Seedream 本地增强层（默认 dry-run）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("image", "video"):
        p = sub.add_parser(name)
        p.add_argument("--prompt", required=True)
        p.add_argument("--out", required=True)
        p.add_argument("--model", default=None)
        p.add_argument("--yes", action="store_true", help="真正提交；不加只打印计划")
        if name == "image":
            p.add_argument("--size", default="2K")
            p.add_argument("--reference", action="append", default=None)
        else:
            p.add_argument("--first-frame", default=None)
            p.add_argument("--last-frame", default=None, help="尾帧；与 --first-frame 一起组成首尾帧模式")
            p.add_argument("--reference", action="append", default=None,
                           help="参考图，可重复；与 --first-frame 互斥（Seedance 2.5 全模态参考）")
            p.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p", "4k"])
            p.add_argument("--ratio", default="16:9")
            p.add_argument("--duration", type=int, default=5)
            p.add_argument("--seed", type=int, default=-1)
            p.add_argument("--camera-fixed", action="store_true")
            p.add_argument("--generate-audio", action="store_true")
            p.add_argument("--frames", action="store_true", help="下载后拆帧给 vclip")
            p.add_argument("--fps", type=int, default=30)
            p.add_argument("--poll", type=int, default=5)
            p.add_argument("--timeout", type=int, default=1800)

    a = sub.add_parser("assets")
    a.add_argument("file")
    a.add_argument("--yes", action="store_true")
    # 让 assets 里的 item 可以覆盖这些默认值
    a.add_argument("--model", default=None)
    a.add_argument("--size", default="2K")
    a.add_argument("--reference", action="append", default=None)
    a.add_argument("--first-frame", default=None)
    a.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p", "4k"])
    a.add_argument("--ratio", default="16:9")
    a.add_argument("--duration", type=int, default=5)
    a.add_argument("--seed", type=int, default=-1)
    a.add_argument("--camera-fixed", action="store_true")
    a.add_argument("--generate-audio", action="store_true")
    a.add_argument("--frames", action="store_true")
    a.add_argument("--fps", type=int, default=30)
    a.add_argument("--poll", type=int, default=5)
    a.add_argument("--timeout", type=int, default=1800)

    args = ap.parse_args()
    if args.cmd == "image":
        gen_image(args)
    elif args.cmd == "video":
        gen_video(args)
    else:
        run_assets(args)


if __name__ == "__main__":
    main()
