# 视频生成工作台

基于火山方舟（Ark）API 的本地 Web 视频/图片生成工作台，实现类似「即梦」的体验：文生视频、图生视频、批量分镜（尾帧衔接）、长片延长、文生图/图生图/组图、ffmpeg 剪辑抽帧。

## 快速开始

```bash
# 1. 创建密钥文件 config.secrets.json（不入 git 仓库）
#    格式见下方「密钥配置」，或运行 run.sh 会打印模板

# 2. 启动（缺失密钥文件会打印指引并退出）
./run.sh
# 或：uvicorn app:app --host 0.0.0.0 --port 8000
```

打开浏览器访问 http://localhost:8000

## 密钥配置（config.secrets.json）

密钥单独放在 `config.secrets.json`（**不入 git，克隆后需自行创建**），`config.json` 只存非敏感配置。

```json
{
  "api_key": "ark-你的火山方舟APIKey",
  "base_url": "https://ark.cn-beijing.volces.com/api/v3",
  "public_base_url": "",
  "access_key_id": "你的AK",
  "secret_access_key": "你的SK",
  "usage_apikey_id": "你的用量APIKeyID"
}
```

- API Key 获取：https://console.volcengine.com/ark/region:cn-beijing/apikey
- 模型开通：https://console.volcengine.com/ark/region:cn-beijing/openManagement
- 也支持环境变量 `ARK_API_KEY` / `ARK_BASE_URL` 覆盖

## config.json（非敏感配置，入库）

改完重启即可。**新增/切换模型只需往这里加条目，前端自动适配。**

| 字段 | 说明 |
|------|------|
| `default_model` | 默认选中哪个模型 |
| `models` | 视频模型下拉（模型 ID → 显示名） |
| `image_models` | 图片模型下拉（Seedream pro / lite） |
| `story_models` | AI 分镜对话模型 |
| `model_caps` | 每个视频模型能力：分辨率/时长/输入/任务类型/素材上限等 |
| `defaults` | 生成参数默认值 |

## 功能

- **视频生成**：文生视频 / 首帧图生 / 首尾帧 / 图生视频
- **多模态参考**：文本 + 图片(首帧/尾帧/参考图) + 参考视频 + 参考音频；提示词 `@图片1/@视频1/@音频1` 引用
- **批量分镜 + 尾帧衔接**：多张图逐段生成，上一段尾帧接下一段首帧，长剧情连续（自动传 `return_last_frame`）
- **长片延长**：参考视频续写，多轮延长直到目标时长（自动 `ratio=adaptive + duration=-1`）
- **图片生成**：Seedream 文生图/图生图/组图；后台异步任务，资产页看进度；多图参考数量限制（pro 2-10 / lite 2-14）；尺寸支持 2K/4K 命名值
- **ffmpeg 剪辑**：视频截取片段（开头/结尾+秒数）；抽帧（前 N 帧/后 N 帧/区间均匀抽帧）
- **资产分类**：🎬 AI生成视频 / ✂ 剪辑视频 / 🖼 AI生成图片 / 🎞 抽帧图片 分类筛选 + 本地位置标注
- **移动资源**：服务端文件夹浏览器，默认 `ai-learning/lzf`，真剪切
- **提示词记录**：每次提交自动追加到 `data/prompts.jsonl`
- **用量/余额查询**、能力页（模型能力对照表）、头像、标签页持久化
- 任务自动轮询，生成视频自动下载本地（规避 URL 24 小时过期）

## 模型

| 模型 | 能力 |
|------|------|
| Seedance 2.0 mini | 480/720p，4-15s，文本+图片（仅首帧），性价比 |
| Seedance 2.0 fast | 480/720p，首尾帧+参考图 |
| Seedance 2.0 | 最高 4k，参考视频/音频、编辑、延长、画面运动、双声道 |
| Seedance 2.5 | 最高 1080p、30s/段、多轮延长、50 素材全模态 |
| Seedream 5.0 pro | 最强画质；多图生图 2-10、图层拆分、交互编辑；不支持组图 |
| Seedream 5.0 lite | 性价比；组图 ≤15 张、多图生图 2-14 |

## 目录结构

```
video-studio/
├── app.py           # FastAPI 后端（接口 + 后台任务）
├── ark_client.py    # 火山方舟 API 封装
├── config.py        # 配置加载（config.json + config.secrets.json 合并）
├── config.json      # 非敏感配置（入库）
├── config.secrets.json # ★ 密钥（不入库，自行创建）
├── store.py         # 任务本地存储（JSON）
├── run.sh           # 启动脚本（缺密钥则退出）
├── static/          # 前端页面
└── data/
    ├── gen_videos/  # 🎬 AI 生成视频
    ├── cut_videos/  # ✂ 剪辑视频
    ├── gen_images/  # 🖼 AI 生成图片
    ├── cut_frames/  # 🎞 抽帧图片
    ├── refs/        # 上传的参考素材
    ├── prompts.jsonl # 提示词提交记录
    └── *.json       # 任务/批量/延长/图片任务记录
```

## 官方文档入口

- 文档中心：https://docs.volcengine.com/docs/ark/?lang=zh
- 开通管理：https://console.volcengine.com/ark/region:cn-beijing/openManagement
- 创建视频生成任务：https://docs.volcengine.com/docs/82379/1520757
- 图片生成 API：https://docs.volcengine.com/docs/82379/1541523
- Seedance 2.5 教程：https://docs.volcengine.com/docs/82379/2607688

## 说明

- 视频 URL 有效期 24 小时，任务成功后立即下载到本地
- Seedance 2.0 mini 并发数为 1，多任务排队
- 任务记录在 `data/*.json`，重启不丢
- 关于 AI 协作会话历史，见仓库根 `OpencodeRecord.md`