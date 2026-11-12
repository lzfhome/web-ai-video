#!/usr/bin/env python3
"""讲解课出片：读镜头表里的段落与音效点 → 生成背景乐和音效（cine/audio/engines/bed.py）→ 混音（旁白压低背景乐）
→ 拼上冷开场画面 → 成片。

用法（用装了 numpy、scipy、playwright 的 Python 跑）：
  CINE_ROOT=<项目根> python line/dom-narrated/finish.py <课号> [--port 8964] [--crf 18] [--encoder x264|nvenc]
输出：lessons/<课号>/build/final_mix.wav、lessons/<课号>/build/lesson<课号>.mp4
"""
import json
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(AIWORK))
import numpy as np
from scipy import signal

from tools.lib.ffmpeg import FFMPEG, nvenc_available, vcodec, probe_fps
from cine.audio.lib.wavio import SR, read_wav, write_wav, fit_to
from cine.audio.lib.dsp import envelope, duck_gain, limiter
from cine.audio.engines.mix import combine, finalize

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

ROOT = Path(os.environ.get("CINE_ROOT") or Path.cwd()).expanduser().resolve()
CINE = AIWORK / "cine"          # 共享引擎；项目里不再放 cine/
FFPROBE = os.environ.get("FFPROBE") or shutil.which("ffprobe") or "ffprobe"


def skill_tools():
    """找 skills/vibe-knowledge/tools；可用 VK_TOOLS 覆盖。"""
    env = os.environ.get("VK_TOOLS")
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "bgm_force.py").exists():
            return p
    p = AIWORK / "skills/vibe-knowledge/tools"
    return p if (p / "bgm_force.py").exists() else None


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def project_fps():
    try:
        return str(json.loads((ROOT / "project.json").read_text(encoding="utf-8")).get("fps", 60))
    except Exception:
        return "60"


def film_info(lesson, port):
    from playwright.sync_api import sync_playwright
    from tools.lib.browser import launch
    from tools.lib.server import serve
    with serve(int(port), ROOT):
        with sync_playwright() as p:
            b = launch(p)
            pg = b.new_page(viewport={"width": 1920, "height": 1080})
            pg.goto(f"http://127.0.0.1:{port}/cine/index.html?lesson={lesson}&capture")
            pg.wait_for_function("window.__film && window.__film.ready", timeout=180000)
            info = pg.evaluate("({from: __film.from, cold: __film.cold, coldSrc: __film.coldSrc, duration: __film.duration, sections: __film.sections, sfx: __film.sfx, clips: __film.clips || [], music: __film.music || []})")
            b.close()
    return info


def main():
    lesson = sys.argv[1]
    port = arg("--port", "8964")
    L = ROOT / "lessons" / lesson
    B = L / "build"
    info = film_info(lesson, port)
    cold, dur, src = float(info["cold"]), float(info["duration"]), info.get("coldSrc")
    total = dur + 0.6
    lj = {"duration": round(total, 3), "bpm": 100, "key": "F minor", "chords": ["Fm", "Db", "Ab", "Eb"],
          "sections": [{"t": round(s["t"], 3), "t_to": round(min(s["t_to"], total), 3), "level": s["level"], "name": s.get("name", "")} for s in info["sections"]],
          "cues": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items()} for c in info["sfx"]]}
    if src:   # 片头拼现成片段：配乐也从同一段原声里截
        lj["cold_open"] = {"from_wav": str(ROOT / src["wav"]), "src_t0": src["t0"], "src_t1": src["t0"] + cold, "at": 0.0}
    (B / "lesson.json").write_text(json.dumps(lj, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"lesson.json：{len(lj['sections'])} 段，{len(lj['cues'])} 个音效点，时长 {total:.2f}s")
    if "--skip-bed" not in sys.argv:
        subprocess.run([sys.executable, str(CINE / "audio/engines/bed.py"), str(B / "lesson.json"), str(B)], check=True)
    n = int(round(total * SR))
    vk = skill_tools()
    if vk is None:
        sys.exit("找不到 skills/vibe-knowledge/tools（强制 BGM 需要 bgm_force.py）；请设置 VK_TOOLS")
    sys.path.insert(0, str(vk)); import bgm_force as VKBGM   # 知识大赏强制 BGM
    _bgm_state = VKBGM.prepare(info, total, B, root=ROOT)
    fit = lambda x: fit_to(x, n)
    bed, sfx = fit(read_wav(B / "bed.wav")), fit(read_wav(B / "sfx.wav"))
    narr = np.zeros((n, 2))
    nv = read_wav(B / "narration.wav")
    i0 = int(round(cold * SR))
    narr[i0:i0 + len(nv)] = nv[: n - i0]
    env = envelope(narr)
    duck = duck_gain(env)                      # 说话时背景乐约 −7 dB
    if src:
        duck[: int(round((cold + 0.25) * SR))] = 1.0   # 拼接的冷开场原样
    # 案例片段的原声：full = 原样放（这段旁白应当是空的、背景乐 level 0）；duck = 压在旁白下面；mute = 不要
    clipa = np.zeros((n, 2))
    bgmt = np.zeros((n, 2))
    for c in info.get("clips", []):
        mode = c.get("audio", "duck")
        if mode == "mute":
            continue
        cpath = L / "assets" / "clips" / f"{c['id']}.mp4"
        tmp = B / f"_clip_{c['id']}.wav"
        r = subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(cpath), "-vn", "-ac", "2", "-ar", str(SR), str(tmp)])
        if r.returncode or not tmp.exists():
            continue
        a = read_wav(tmp); tmp.unlink()
        k = int(0.12 * SR)
        if len(a) > 2 * k:
            ramp = np.linspace(0, 1, k)[:, None]; a[:k] *= ramp; a[-k:] *= ramp[::-1]
        g = 10 ** (c.get("gain", -2.0 if mode == "full" else -15.0) / 20)
        j0 = int(round(c["at"] * SR)); j1 = min(n, j0 + len(a))
        if j1 > j0:
            clipa[j0:j1] += a[: j1 - j0] * g
    # 整段配乐插入（例如导学开场的高光快剪用曲库里的一首）：{src 绝对路径, from 源内起点, at, dur, gain dB, fade_in, fade_out}；有旁白时同样被压低
    # earshot 代码音效（vibe-knowledge patch_earshot）：src 写 "earshot:<id>" 的条目先统一渲染（按参数哈希缓存），再按 onset / peak 对齐到 at
    import hashlib, os
    es_jobs = []
    for m in info.get("music", []):
        if str(m.get("src", "")).startswith("earshot:"):
            o = m.get("es") or {}
            j = {"id": str(m["src"])[8:], "seed": o.get("seed"), "dur": o.get("dur"), "apex": o.get("apex"), "pitch": o.get("pitch")}
            j["key"] = hashlib.md5(json.dumps(j, sort_keys=True).encode()).hexdigest()[:12]
            m["_es"] = j
            if j not in es_jobs:
                es_jobs.append(j)
    if es_jobs:
        esd = B / "esfx"; esd.mkdir(exist_ok=True)
        (esd / "jobs.json").write_text(json.dumps(es_jobs, ensure_ascii=False), encoding="utf-8")
        py = os.environ.get("EARSHOT_PY")
        if not py:
            for cand in (Path.home() / "tools/earshot/.venv/bin/python",
                         Path.home() / "tools/earshot/.venv/Scripts/python.exe"):
                if cand.exists():
                    py = str(cand)
                    break
        py = py or sys.executable
        tool = os.environ.get("EARSHOT_TOOL")
        if not tool:
            tool = str(vk / "earshot_render.py") if vk else str(Path("earshot_render.py"))
        subprocess.run([py, tool, str(esd / "jobs.json"), str(esd)], check=True, env={**os.environ, "PYTHONPATH": ""})
        for m in info.get("music", []):
            if "_es" in m:
                meta = json.loads((esd / f"{m['_es']['key']}.json").read_text(encoding="utf-8"))
                lead = float(meta.get("peak_s" if m.get("align") == "peak" else "onset_s") or 0)
                m["src"] = str(esd / f"{m['_es']['key']}.wav")
                m["dur"] = float(meta.get("dur_s") or m.get("dur", 3))
                m["from"] = max(0.0, lead - float(m["at"]))          # at 太靠前时从文件中间截
                m["at"] = max(0.0, float(m["at"]) - lead)
                m.setdefault("fade_in", 0.0); m.setdefault("fade_out", 0.02)
                print(f"  earshot {meta.get('id')} → {m['at']:.3f}s（{m.get('align', 'onset')} 对齐，提前 {lead * 1000:.0f} ms）")
    for m in info.get("music", []):
        tmp = B / "_music.wav"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", f"{float(m.get('from', 0)):.3f}", "-t", f"{float(m['dur']):.3f}", "-i", str(m["src"] if Path(m["src"]).is_absolute() else ROOT / m["src"]),
                        "-vn", "-ac", "2", "-ar", str(SR), str(tmp)], check=True)
        a = read_wav(tmp); tmp.unlink()
        ki, ko = int(float(m.get("fade_in", 0.03)) * SR), int(float(m.get("fade_out", 1.2)) * SR)
        if ki: a[:ki] *= np.linspace(0, 1, ki)[:, None]
        if ko and len(a) > ko: a[-ko:] *= np.linspace(1, 0, ko)[:, None]
        j0 = int(round(float(m["at"]) * SR)); j1 = min(n, j0 + len(a))
        if j1 > j0:
            if m.get("gain_curve"):     # 分段音量：[[片中秒, dB], …] 线性插值，比如冷开场满音量、旁白段压低
                pts = np.array(m["gain_curve"], dtype=np.float64)
                tt = np.arange(j0, j1) / SR
                g = 10 ** (np.interp(tt, pts[:, 0], pts[:, 1]) / 20)
            else:
                g = np.full(j1 - j0, 10 ** (float(m.get("gain", -4.0)) / 20))
            dk = duck[j0:j1] if m.get("duck", "_es" not in m) else 1.0   # earshot 音效默认不压
            (bgmt if m.get("_bgm") else clipa)[j0:j1] += a[: j1 - j0] * (g * dk)[:, None]
    clipa += VKBGM.calibrate(bgmt, narr, env > 0.5, B, _bgm_state)
    mix = combine(narr, bed, sfx, clipa, duck)
    # 响度：按有旁白的部分对齐到约 −16 dBFS RMS
    speech = env > 0.5
    mix = finalize(mix, speech)
    write_wav(B / "final_mix.wav", mix)
    print(f"混音 → {B / 'final_mix.wav'}  峰值 {20 * np.log10(np.max(np.abs(mix)) + 1e-9):.1f} dBFS")
    if "--audio-only" in sys.argv:
        return
    # 画面：有 COLD_SRC 时先拼那段现成画面，再接本课渲染；然后把案例片段逐段叠到各自的框里
    fps = int(arg("--fps", project_fps()))
    crf = arg("--crf", "18")
    encoder = arg("--encoder", "x264").lower()
    if encoder == "nvenc" and not nvenc_available():
        print("⚠ NVENC 不可用（NVIDIA 驱动/ffmpeg 版本不匹配），回退 x264")
        encoder = "x264"
    out = B / f"lesson{lesson}.mp4"
    picture = B / "picture.mp4"
    pic_fps = probe_fps(picture)
    need_encode = bool(src) or bool(info.get("clips")) or pic_fps is None or abs(pic_fps - fps) > 0.01
    if not need_encode:
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(picture), "-i", str(B / "final_mix.wav"),
                        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", "-movflags", "+faststart", str(out)], check=True)
        print(f"成片（视频流直接 copy，无重编码）→ {out}")
        return
    if pic_fps and abs(pic_fps - fps) > 0.01:
        print(f"  picture {pic_fps:g}fps ≠ 目标 {fps}fps，重编码")
    ins, fc = [], []
    if src:
        a0, na = round(src["t0"] * fps), round(cold * fps)
        ins += ["-i", str(ROOT / src["video"]), "-i", str(B / "picture.mp4")]
        fc.append(f"[0:v]trim=start_frame={a0}:end_frame={a0 + na},setpts=PTS-STARTPTS[ca];[1:v]setpts=PTS-STARTPTS[cb];[ca][cb]concat=n=2:v=1:a=0[base]")
        k0 = 2
    else:
        ins += ["-i", str(B / "picture.mp4")]
        fc.append("[0:v]setpts=PTS-STARTPTS[base]")
        k0 = 1
    last = "base"
    for i, c in enumerate(info.get("clips", [])):
        ins += ["-i", str(L / "assets" / "clips" / f"{c['id']}.mp4")]
        k, at, d = k0 + i, float(c["at"]), float(c["dur"])
        fd = float(c.get("fade", 0.15))
        fades = f",fade=t=in:st={at:.4f}:d={fd:.3f}:alpha=1,fade=t=out:st={at + d - fd:.4f}:d={fd:.3f}:alpha=1" if fd > 0 else ""
        fc.append(f"[{k}:v]setpts=PTS-STARTPTS+{at:.4f}/TB,format=yuva420p{fades}[c{i}]")
        fc.append(f"[{last}][c{i}]overlay={int(c['x'])}:{int(c['y'])}:enable='between(t,{at:.4f},{at + d:.4f})':eof_action=pass[v{i}]")
        last = f"v{i}"
    ins += ["-i", str(B / "final_mix.wav")]
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", f"{len(ins) // 2 - 1}:a",
                    *vcodec(encoder, crf), "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)], check=True)
    print(f"成片 → {out}")


if __name__ == "__main__":
    main()
