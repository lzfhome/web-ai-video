import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
SECRETS_PATH = ROOT / "config.secrets.json"

SECRET_KEYS = {
    "api_key", "base_url", "public_base_url",
    "access_key_id", "secret_access_key", "usage_apikey_id",
}

DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "public_base_url": "",
    "access_key_id": "",
    "secret_access_key": "",
    "usage_apikey_id": "",
    "story_model": "deepseek-v4-1-flash-260910",
    "story_models": {
        "deepseek-v4-1-flash-260910": "DeepSeek V4.1 Flash",
        "deepseek-v4-flash": "DeepSeek V4 Flash",
        "deepseek-v4-pro": "DeepSeek V4 Pro",
        "deepseek-v3.2": "DeepSeek V3.2",
        "doubao-seed-1-6-260628": "豆包 Seed 1.6",
        "doubao-1-5-pro-32k-250115": "Doubao 1.5 Pro 32k",
        "glm-5.3": "智谱 GLM 5.3",
        "glm-5.1": "智谱 GLM 5.1",
        "glm-4.7": "智谱 GLM 4.7",
        "kimi-k2.5": "Kimi K2.5",
        "kimi-k2": "Kimi K2",
        "minimax-m2.5": "MiniMax M2.5",
    },
    "image_model": "doubao-seedream-5-0-260128",
    "image_models": {
        "doubao-seedream-5-0-pro-260628": "Seedream 5.0 pro（最强）",
        "doubao-seedream-5-0-260128": "Seedream 5.0 lite（最划算）",
    },
    "default_model": "doubao-seedance-2-0-mini-260615",
    "models": {
        "doubao-seedance-2-0-mini-260615": "Seedance 2.0 mini（高性价比 · 480p/720p）",
        "doubao-seedance-2-0-fast-260128": "Seedance 2.0 fast（快速 · 480p/720p）",
        "doubao-seedance-2-0-260128": "Seedance 2.0（专业级 · 最高 4k）",
        "doubao-seedance-2-5-260628": "Seedance 2.5（长叙事 · 最高 1080p）",
    },
    "model_caps": {
        "doubao-seedance-2-0-mini-260615": {
            "resolutions": ["480p", "720p"], "max_duration": 15,
            "inputs": ["text", "image"], "task_types": ["auto"],
            "roles": ["first_frame"], "camera_fixed": False, "max_media": 10,
            "features": ["文生视频", "首帧图生", "有声视频", "返回尾帧", "480p/720p", "4-15秒"],
        },
        "doubao-seedance-2-0-fast-260128": {
            "resolutions": ["480p", "720p"], "max_duration": 15,
            "inputs": ["text", "image"], "task_types": ["auto"],
            "roles": ["first_frame", "last_frame", "reference_image"], "camera_fixed": False, "max_media": 10,
            "features": ["文生视频", "首帧图生", "首尾帧", "参考图", "有声视频", "返回尾帧", "480p/720p", "4-15秒"],
        },
        "doubao-seedance-2-0-260128": {
            "resolutions": ["480p", "720p", "1080p", "4k"], "max_duration": 15,
            "inputs": ["text", "image", "video", "audio"],
            "task_types": ["auto", "text", "image", "edit", "extend"],
            "roles": ["first_frame", "last_frame", "reference_image"], "camera_fixed": True, "max_media": 20,
            "features": ["文生视频", "首帧图生", "首尾帧", "参考图/视频/音频", "视频编辑", "视频延长", "有声视频", "画面运动", "联网搜索", "最高4K", "4-15秒"],
        },
        "doubao-seedance-2-5-260628": {
            "resolutions": ["480p", "720p", "1080p"], "max_duration": 30,
            "inputs": ["text", "image", "video", "audio"],
            "task_types": ["auto", "text", "image", "edit", "extend"],
            "roles": ["first_frame", "last_frame", "reference_image"], "camera_fixed": True, "max_media": 50,
            "features": ["文生视频", "首帧图生", "首尾帧", "全模态参考(50素材)", "视频编辑", "多轮延长", "长叙事30秒", "有声视频", "画面运动", "最高1080p"],
        },
    },
    "defaults": {
        "resolution": "720p",
        "ratio": "16:9",
        "duration": 5,
        "seed": -1,
        "camera_fixed": False,
        "watermark": False,
        "generate_audio": True,
        "task_type": "auto",
    },
}


def load_config() -> dict:
    cfg = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cfg = {}

    # 密钥单独文件（不入库）：config.secrets.json 覆盖 config.json
    secrets = {}
    if SECRETS_PATH.exists():
        try:
            secrets = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            secrets = {}
    for k in SECRET_KEYS:
        if k in secrets:
            cfg[k] = secrets[k]

    merged = {**DEFAULT_CONFIG, **cfg}
    if isinstance(merged.get("models"), dict):
        merged["models"] = {**DEFAULT_CONFIG["models"], **merged["models"]}
    if isinstance(merged.get("story_models"), dict):
        merged["story_models"] = {**DEFAULT_CONFIG["story_models"], **merged["story_models"]}
    if isinstance(merged.get("image_models"), dict):
        merged["image_models"] = {**DEFAULT_CONFIG["image_models"], **merged["image_models"]}
    if isinstance(merged.get("defaults"), dict):
        merged["defaults"] = {**DEFAULT_CONFIG["defaults"], **merged["defaults"]}
    if isinstance(merged.get("model_caps"), dict):
        caps = {}
        for mid, cap in merged["model_caps"].items():
            base = DEFAULT_CONFIG["model_caps"].get(mid, {})
            if isinstance(cap, dict):
                caps[mid] = {**base, **cap}
            else:
                caps[mid] = base
        merged["model_caps"] = caps

    # 环境变量可覆盖（可选，方便 CI / 部署）
    if os.environ.get("ARK_API_KEY"):
        merged["api_key"] = os.environ["ARK_API_KEY"]
    if os.environ.get("ARK_BASE_URL"):
        merged["base_url"] = os.environ["ARK_BASE_URL"]
    return merged


CONFIG = load_config()