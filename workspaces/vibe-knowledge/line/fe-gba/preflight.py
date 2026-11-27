#!/usr/bin/env python3
"""fe-gba 预检：只读 work.json，打印计划；不调用任何付费 API。

用法：
  python workspaces/vibe-knowledge/line/fe-gba/preflight.py <work.json>
  python workspaces/vibe-knowledge/line/fe-gba/preflight.py <work.json> --allow-missing
"""
import argparse
import json
import sys
from pathlib import Path

LINE = Path(__file__).resolve().parent
AIWORK = LINE.parents[3]
DEFAULTS = json.loads((LINE / "defaults.json").read_text(encoding="utf-8"))

MODEL_LIMITS = {
    "doubao-seedance-2-5-flash-261115": {"res": {"480p", "720p"}, "duration": (4, 30)},
    "doubao-seedance-2-5-260628": {"res": {"480p", "720p", "1080p", "4k"}, "duration": (4, 30)},
}
RATIOS = {"16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"}
MODES = {"first_frame", "reference", "text"}


def resolve(base: Path, p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else (base / q)


def validate(work: dict, base: Path, allow_missing: bool = False):
    errors, warnings = [], []
    if not str(work.get("title") or "").strip():
        errors.append("title 不能为空")
    if len(str(work.get("story") or "").strip()) < 10:
        errors.append("story 至少写一句完整剧情（≥10 字）")
    if len(str(work.get("style") or "").strip()) < 10:
        errors.append("style 至少写清画风（≥10 字）")
    if not str(work.get("style_lock") or "").strip():
        warnings.append("style_lock 为空：角色服装/发型/武器容易漂")

    shots = work.get("shots")
    if not isinstance(shots, list) or not shots:
        errors.append("shots 必须是非空数组")
        return errors, warnings, []

    plan = []
    for i, shot in enumerate(shots):
        sid = str(shot.get("id") or f"S{i + 1:02d}")
        tag = f"shots[{i}] ({sid})"
        mode = shot.get("mode") or "first_frame"
        if mode not in MODES:
            errors.append(f"{tag}.mode 必须是 {', '.join(sorted(MODES))}")

        if len(str(shot.get("story") or "").strip()) < 10:
            errors.append(f"{tag}.story 至少写一句完整剧情（≥10 字）")
        action = shot.get("action") or {}
        if not isinstance(action, dict) or not all(str(action.get(k) or "").strip() for k in ("start", "middle", "end")):
            errors.append(f"{tag}.action 必须写全 start / middle / end")
        if len(str(shot.get("camera") or "").strip()) < 3:
            errors.append(f"{tag}.camera 不能为空（推/拉/摇/固定）")
        if len(str(shot.get("video_prompt") or "").strip()) < 40:
            errors.append(f"{tag}.video_prompt 至少 40 字，写清动作/镜头/连续性")

        refs = shot.get("reference_images") or []
        if not isinstance(refs, list) or len(refs) > 10:
            errors.append(f"{tag}.reference_images 必须是 0–10 张的数组")
            refs = []
        for r in refs:
            p = resolve(base, str(r))
            if not p.exists() and not allow_missing:
                errors.append(f"{tag} 参考图不存在：{p}")

        keyframe = shot.get("keyframe")
        last_frame = shot.get("last_frame")
        if last_frame:
            lf = resolve(base, str(last_frame))
            if not lf.exists() and not allow_missing:
                errors.append(f"{tag} 尾帧不存在：{lf}")
            if mode != "first_frame":
                warnings.append(f"{tag} 有 last_frame，但 mode 不是 first_frame；首尾帧模式需要 first_frame")
        if mode == "first_frame":
            if not keyframe:
                errors.append(f"{tag}.keyframe 在 first_frame 模式必填")
            else:
                kp = resolve(base, str(keyframe))
                if not kp.exists():
                    if len(str(shot.get("keyframe_prompt") or "").strip()) < 40:
                        errors.append(f"{tag} 还没有帧图，且 keyframe_prompt 少于 40 字")
                    if not refs:
                        warnings.append(f"{tag} 没有参考图，帧图角色容易漂")
                elif kp.stat().st_size == 0:
                    errors.append(f"{tag} 帧图是空文件：{kp}")
        elif mode == "reference" and not refs:
            errors.append(f"{tag} reference 模式至少要 1 张参考图")
        elif mode == "text":
            warnings.append(f"{tag} 是 text 模式：只测文生视频，不保证角色一致性")

        model = shot.get("model") or DEFAULTS["video_model"]
        if model not in MODEL_LIMITS:
            errors.append(f"{tag}.model 不在本产线允许列表：{model}")
        limits = MODEL_LIMITS.get(model, {})
        res = str(shot.get("resolution") or DEFAULTS["resolution"])
        if res not in limits.get("res", set()):
            errors.append(f"{tag}.resolution={res} 不被 {model} 支持；可选 {', '.join(sorted(limits.get('res', set())))}")
        try:
            duration = int(shot.get("duration", DEFAULTS["duration"]))
        except (TypeError, ValueError):
            duration = 0
        lo, hi = limits.get("duration", (4, 30))
        if not lo <= duration <= hi:
            errors.append(f"{tag}.duration 必须在 {lo}–{hi} 秒")

        ratio = str(shot.get("ratio") or DEFAULTS["ratio"])
        if ratio not in RATIOS:
            errors.append(f"{tag}.ratio 不支持：{ratio}")
        if mode == "first_frame" and model.startswith("doubao-seedance-2-5") and ratio != "adaptive":
            warnings.append(f"{tag} 是 2.5 首帧：引擎会强制 ratio=adaptive（配置写 {ratio} 只是记录）")

        seed = shot.get("seed", DEFAULTS["seed"])
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            errors.append(f"{tag}.seed 必须是固定非负整数；禁止 -1 随机抽卡")
        try:
            max_takes = int(shot.get("max_takes", DEFAULTS["max_takes"]))
        except (TypeError, ValueError):
            max_takes = 0
        if max_takes != 1:
            errors.append(f"{tag}.max_takes 必须是 1；要重跑请改描述并显式 --force")

        video = shot.get("video") or f"build/{sid}.mp4"
        vp = resolve(base, str(video))
        if vp.exists():
            warnings.append(f"{tag} 输出已存在，render 默认会跳过：{vp}")

        plan.append({
            "id": sid,
            "model": model,
            "duration": duration,
            "resolution": res,
            "ratio": ratio,
            "seed": seed,
            "mode": mode,
            "keyframe": str(resolve(base, str(keyframe))) if keyframe else "",
            "last_frame": str(resolve(base, str(last_frame))) if last_frame else "",
            "video": str(vp),
            "refs": [str(resolve(base, str(r))) for r in refs],
        })
    return errors, warnings, plan


def main():
    ap = argparse.ArgumentParser(description="fe-gba 预检（只读，不调用 API）")
    ap.add_argument("work", help="work.json 路径")
    ap.add_argument("--allow-missing", action="store_true", help="允许参考图/帧图暂时不存在")
    args = ap.parse_args()

    path = Path(args.work).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"找不到 work.json：{path}")
    work = json.loads(path.read_text(encoding="utf-8"))
    errors, warnings, plan = validate(work, path.parent, args.allow_missing)

    print(f"work: {path}")
    print(f"title: {work.get('title', '')}")
    print(f"shots: {len(plan)}")
    for p in plan:
        print(f"  {p['id']}: {p['model']} · {p['duration']}s · {p['resolution']} · {p['ratio']} · seed {p['seed']} · {p['mode']}")
        if p["refs"]:
            print(f"    refs: {', '.join(p['refs'])}")
        print(f"    keyframe: {p['keyframe'] or '—'}")
        print(f"    video: {p['video']}")
    for w in warnings:
        print(f"⚠ {w}")
    if errors:
        print("\n✗ 预检失败：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("\n✓ 预检通过（未调用 API）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
