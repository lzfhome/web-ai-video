#!/usr/bin/env python3
"""讲解课逐帧录制：python cine/video/engines/dom/record.py <课号> [--from 秒] [--to 秒] [--port 8964]
       [--fps 30] [--crf 16] [--shot jpeg|png] [--workers 4] [--encoder x264|nvenc]

从冷开场之后（film.COLD）渲到旁白结束；film.blur 里的时间段做子帧运动模糊。
输出 lessons/<课号>/build/picture.mp4

--workers N：把时间轴切成 N 段，每段一个浏览器进程并行渲染，最后无损 concat。
默认 1；稳定上限 4（6/8 路会因浏览器实例过多卡在页面加载）。编码仍是同一个 x264/CRF，质量不变。
--encoder nvenc：中间片改用 GPU 编码（h264_nvenc，CQ≈crf）；速度快，但同码率画质略低于 x264。
--pipe auto|jpeg|raw：auto 在无 motion blur 时把 Chrome 的 JPEG 直接送 ffmpeg（省掉 PIL 解码和 raw RGB 管道）；
  raw 强制走旧的 PIL → rawvideo 路径。
默认 JPEG q95 截图（快）；短片的字卡/文字特别多时可用 --shot png，画质更好但慢约 5 倍。
"""
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from tools.lib.browser import launch
from tools.lib.ffmpeg import FFMPEG, nvenc_available, vcodec
from tools.lib.server import serve

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

ROOT = Path(os.environ.get("CINE_ROOT") or Path.cwd()).expanduser().resolve()


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def project_fps():
    try:
        return str(json.loads((ROOT / "project.json").read_text(encoding="utf-8")).get("fps", 60))
    except Exception:
        return "60"


def film_info(lesson, port):
    with sync_playwright() as p:
        b = launch(p)
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto(f"http://127.0.0.1:{port}/cine/index.html?lesson={lesson}&capture")
        pg.wait_for_function("window.__film && window.__film.ready", timeout=180000)
        info = pg.evaluate("({from: __film.from, duration: __film.duration, blur: __film.blur})")
        b.close()
    return info


def render_range(lesson, port, crf, fps, shot_fmt, out, t0=None, t1=None, encoder="x264", pipe="auto"):
    with sync_playwright() as p:
        b = launch(p)
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/cine/index.html?lesson={lesson}&capture")
        pg.wait_for_function("window.__film && window.__film.ready", timeout=180000)
        info = pg.evaluate("({from: __film.from, duration: __film.duration, blur: __film.blur})")
        t0 = float(info["from"] if t0 is None else t0)
        t1 = float(info["duration"] if t1 is None else t1)
        n0, n1 = round(t0 * fps), round(t1 * fps)
        use_jpeg_pipe = shot_fmt == "jpeg" and not info["blur"] and pipe in ("auto", "jpeg")
        if use_jpeg_pipe:
            enc = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-vcodec", "mjpeg",
                                    "-r", str(fps), "-i", "-", *vcodec(encoder, crf),
                                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
                                   stdin=subprocess.PIPE)
        else:
            enc = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                    "-s", "1920x1080", "-r", str(fps), "-i", "-", *vcodec(encoder, crf),
                                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
                                   stdin=subprocess.PIPE)
        st = time.time()

        def seek(t):
            pg.evaluate("(t) => window.__film.seek(t)", t)
            pg.evaluate("() => window.__vk ? window.__vk.wait() : null")

        def shot(t):
            seek(t)
            kw = {"type": shot_fmt}
            if shot_fmt == "jpeg":
                kw["quality"] = 95
            return np.asarray(Image.open(io.BytesIO(pg.screenshot(**kw))).convert("RGB"))

        try:
            for i in range(n0, n1):
                t = i / fps
                try:
                    if use_jpeg_pipe:
                        seek(t)
                        enc.stdin.write(pg.screenshot(type="jpeg", quality=95))
                    else:
                        if any(a <= t < z for a, z in info["blur"]):
                            k = 4
                            acc = np.zeros((1080, 1920, 3), np.float32)
                            for j in range(k):
                                acc += shot(t + ((j + 0.5) / k - 0.5) * 0.5 / fps).astype(np.float32)
                            frame = (acc / k + 0.5).astype(np.uint8)
                        else:
                            frame = shot(t)
                        enc.stdin.write(frame.tobytes())
                except (BrokenPipeError, OSError) as exc:
                    raise SystemExit(f"ffmpeg 编码失败（编码器 {encoder}）：{exc}")
                if (i - n0) % 600 == 0:
                    el, done = time.time() - st, i - n0 + 1
                    print(f"  {t:7.2f}s  {done}/{n1 - n0}  {el:5.0f}s  ≈剩 {el / done * (n1 - n0 - done):5.0f}s", flush=True)
        finally:
            try:
                enc.stdin.close()
            except (BrokenPipeError, OSError):
                pass
            enc.wait()
            b.close()
    if errs:
        print("页面报错：", errs[:5])
    return time.time() - st


def concat_parts(parts, out):
    lst = out.parent / f".{out.stem}.concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    try:
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    finally:
        lst.unlink(missing_ok=True)


def main():
    lesson = sys.argv[1]
    port, crf = arg("--port", "8964"), arg("--crf", "16")
    fps = int(arg("--fps", project_fps()))
    shot_fmt = arg("--shot", "jpeg").lower()
    workers = max(1, int(arg("--workers", "1")))
    workers = min(workers, 4, max(1, os.cpu_count() or 1))
    encoder = arg("--encoder", "x264").lower()
    pipe = arg("--pipe", "auto").lower()
    if shot_fmt not in ("png", "jpeg"):
        raise SystemExit("--shot 只能是 png 或 jpeg")
    if encoder not in ("x264", "nvenc"):
        raise SystemExit("--encoder 只能是 x264 或 nvenc")
    if pipe not in ("auto", "jpeg", "raw"):
        raise SystemExit("--pipe 只能是 auto / jpeg / raw")
    if encoder == "nvenc" and not nvenc_available():
        print("⚠ NVENC 不可用（NVIDIA 驱动/ffmpeg 版本不匹配），回退 x264")
        encoder = "x264"
    out = ROOT / "lessons" / lesson / "build" / arg("--out", "picture.mp4")
    t0_arg, t1_arg = arg("--from", None), arg("--to", None)

    with serve(int(port), ROOT):
        if workers <= 1:
            elapsed = render_range(lesson, port, crf, fps, shot_fmt, out, t0_arg, t1_arg, encoder, pipe)
            print(f"→ {out}  ({elapsed:.0f}s, {fps}fps, crf {crf}, {shot_fmt}, {encoder}, pipe {pipe})")
            return

        info = film_info(lesson, port)
        n0 = round(float(info["from"] if t0_arg is None else t0_arg) * fps)
        n1 = round(float(info["duration"] if t1_arg is None else t1_arg) * fps)
        total = n1 - n0
        workers = min(workers, max(1, total))
        per = (total + workers - 1) // workers
        parts, procs = [], []
        st = time.time()
        for k in range(workers):
            a, z = n0 + k * per, min(n1, n0 + (k + 1) * per)
            if a >= z:
                break
            part = out.parent / f".{out.stem}.part{k}{out.suffix}"
            part.unlink(missing_ok=True)
            cmd = [sys.executable, str(Path(__file__).resolve()), lesson,
                   "--port", port, "--fps", str(fps), "--crf", crf, "--shot", shot_fmt,
                   "--workers", "1", "--encoder", encoder, "--pipe", pipe,
                   "--from", f"{a / fps:.6f}", "--to", f"{z / fps:.6f}", "--out", part.name]
            print(f"  worker {k}: {a / fps:.2f}s → {z / fps:.2f}s", flush=True)
            procs.append((subprocess.Popen(cmd), part, a, z))
        failed = False
        for p, part, a, z in procs:
            if p.wait() != 0:
                failed = True
                break
        if failed:
            for p, _, _, _ in procs:
                if p.poll() is None:
                    p.kill()
            for _, part, _, _ in procs:
                try:
                    part.unlink(missing_ok=True)
                except OSError:
                    pass
            raise SystemExit("并行渲染失败")
        parts = [part for _, part, _, _ in procs]
        concat_parts(parts, out)
        for part in parts:
            part.unlink(missing_ok=True)
        print(f"→ {out}  ({time.time() - st:.0f}s, {fps}fps, crf {crf}, {shot_fmt}, {encoder}, pipe {pipe}, {len(parts)} workers)")


if __name__ == "__main__":
    main()
