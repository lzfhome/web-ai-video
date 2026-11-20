#!/usr/bin/env python3
"""右上角文字水印：给单个视频或目录批量叠加。

默认只打印计划，确认后加 --yes。

用法：
  python cine/video/engines/watermark.py video.mp4 --text "B站@__小凡__"
  python cine/video/engines/watermark.py deliveries --text "B站@__小凡__" --recursive --yes
  python cine/video/engines/watermark.py video.mp4 --text "B站@__小凡__" --inplace --yes

默认输出：<原名>_wm.mp4；--inplace 先备份 .bak 再替换原文件。
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

DEFAULT_FONT = r"C:/Windows/Fonts/msyh.ttc"
DEFAULT_TEXT = "B站@__小凡__"


def esc_text(s):
    # ffmpeg drawtext 需要转义 : ' \ %
    return (
        s.replace("\\", r"\\")
        .replace(":", r"\:")
        .replace("'", r"\'")
        .replace("%", r"\%")
    )


def esc_font(path):
    # Windows 盘符的冒号要转义；反斜杠改成正斜杠
    return str(path).replace("\\", "/").replace(":", r"\:")


def build_filter(font, text, opacity, font_ratio, margin_ratio):
    return (
        "drawtext="
        "fontfile='%s':"
        "text='%s':"
        "fontcolor=white@%s:"
        "fontsize=h*%s:"
        "x=w-tw-w*%s:"
        "y=h*%s:"
        "shadowcolor=black@0.35:shadowx=1:shadowy=1"
        % (
            esc_font(font),
            esc_text(text),
            opacity,
            font_ratio,
            margin_ratio,
            margin_ratio,
        )
    )


def find_videos(path, recursive):
    if path.is_file():
        return [path]
    pattern = "**/*.mp4" if recursive else "*.mp4"
    return sorted(p for p in path.glob(pattern) if p.is_file() and not p.stem.endswith("_wm"))


def main():
    ap = argparse.ArgumentParser(description="右上角文字水印（默认 dry-run）")
    ap.add_argument("path", help="视频文件或目录")
    ap.add_argument("--text", default=DEFAULT_TEXT)
    ap.add_argument("--font", default=DEFAULT_FONT)
    ap.add_argument("--opacity", default="0.35")
    ap.add_argument("--font-ratio", default="0.028")
    ap.add_argument("--margin-ratio", default="0.03")
    ap.add_argument("--suffix", default="_wm")
    ap.add_argument("--inplace", action="store_true")
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    path = Path(args.path).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"找不到：{path}")
    if not Path(args.font).exists():
        raise SystemExit(f"找不到字体：{args.font}")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("找不到 ffmpeg，先确认 PATH 或设置 FFMPEG")

    videos = find_videos(path, args.recursive)
    if not videos:
        raise SystemExit(f"{path} 下没有 mp4")

    vf = build_filter(args.font, args.text, args.opacity, args.font_ratio, args.margin_ratio)
    print(f"水印：{args.text}")
    print(f"字体：{args.font}")
    print(f"位置：右上角，边距 {args.margin_ratio}，字号 h*{args.font_ratio}，透明度 {args.opacity}")
    print(f"视频：{len(videos)} 个")

    for src in videos:
        if src.stem.endswith("_wm"):
            continue
        if args.inplace:
            dst = src.with_name(src.stem + ".wm.tmp" + src.suffix)
        else:
            dst = src.with_name(src.stem + args.suffix + src.suffix)
        cmd = [
            ffmpeg, "-y", "-loglevel", "error", "-i", str(src),
            "-vf", vf,
            "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
            str(dst),
        ]
        print(f"\n== {src.name} ==")
        print("out:", dst.name)
        if not args.yes:
            print("  （dry-run：未执行）")
            continue
        subprocess.run(cmd, check=True)
        if args.inplace:
            bak = src.with_name(src.stem + ".bak" + src.suffix)
            if bak.exists():
                bak.unlink()
            src.replace(bak)
            dst.replace(src)
            print(f"  ✓ {src.name}（原文件备份 {bak.name}）")
        else:
            print(f"  ✓ {dst.name}")

    if not args.yes:
        print("\n确认后加 --yes")


if __name__ == "__main__":
    main()
