# 视频生成工作台

基于火山方舟（Ark）视频生成 API 的本地 Web 小站，实现类似「即梦」的丝滑体验：上传图片 + 填写提示词 → 生成视频 → 在线播放/下载。

## 快速开始

```bash
# 1. 配置 API Key：编辑 config.json，填入你的 api_key
#    获取地址：https://console.volcengine.com/ark/region:cn-beijing/apikey

# 2. 启动
./run.sh
```

打开浏览器访问 http://localhost:8000

## config.json

所有配置都在这个文件里，改完重启即可。**新增/切换模型只需往这里加条目，前端自动适配。**

| 字段 | 说明 |
|------|------|
| `api_key` | 火山方舟 API Key（必填） |
| `base_url` | API 地址，一般不用改 |
| `public_base_url` | 公网隧道地址（可选）。本地上传视频做参考时需要，如 `https://xxx.ngrok-free.app` |
| `default_model` | 默认选中哪个模型 |
| `models` | 模型下拉框可选项（模型 ID → 显示名） |
| `model_caps` | 每个模型的能力：`resolutions`（分辨率）、`max_duration`（最长秒数）、`inputs`（支持的输入：text/image/video/audio）、`task_types`（任务类型：auto/text/image/edit/extend）、`max_media`（素材数量上限） |
| `defaults` | 生成参数默认值 |

### 新增一个模型

在 `models` 加一行显示名，在 `model_caps` 加一条能力配置，重启即可出现在下拉框。

## 功能

- **多模态输入**：提示词（text）+ 图片（首帧/尾帧/参考图）+ 参考视频（URL）+ 参考音频（文件或 URL），自由组合
- **任务类型**：自动判断 / 文生视频 / 图生视频 / 视频编辑 / 视频延长
- **模型切换**：下拉选择，分辨率、时长、输入类型、任务类型、素材上限随模型自动适配
  - Seedance 2.0 mini / fast：仅 480p/720p，文本+图片
  - Seedance 2.0：最高 4k，支持视频/音频参考、编辑、延长
  - Seedance 2.5：最高 1080p、最长 30s，支持编辑、延长、全模态
- **参数自动适配**：编辑/延长/首尾帧任务自动锁定 `ratio=adaptive`、`duration=-1`
- 图生视频：首帧 / 尾帧 / 参考图 三种图片角色
- 任务自动轮询：排队中 → 生成中 → 已完成 / 失败
- 生成视频自动下载到本地 `data/videos/`（规避 URL 24 小时过期问题）
- 在线播放 + 一键下载

## 素材输入能力

| 素材 | 本地上传 | 说明 |
|------|---------|------|
| 图片 | ✅ | 自动转 base64，可多选；角色可选 首帧/尾帧/参考图 |
| 音频 | ✅ | 自动转 base64（API 支持音频 base64） |
| 视频 | ⚠ 有条件 | 方舟视频生成 API **只接受公网 URL，不支持 base64**。可「粘贴公网 URL」直接引用；或「上传本地视频」后需在 `config.json` 配置 `public_base_url`（公网隧道地址，如 ngrok/cloudflared），平台会拼出可访问地址供方舟拉取 |

> 启隧道示例：`ngrok http 8000` 得到 `https://xxx.ngrok-free.app`，填入 `public_base_url` 后重启。生成期间保持隧道开启。

## 提示词技巧

素材可在提示词中引用：`@图片1` / `@视频1` / `@音频1`（按同类型素材的添加顺序编号）。
例如：`首帧为 @图片1，参考 @视频1 的运镜，用 @音频1 作为背景音乐。`

> 参考视频必须是公网可访问的 URL（本地文件无法被方舟服务器访问）。图片、音频支持本地上传（自动转 base64）。

### 视频延长 / 编辑 快捷用法

**视频延长（续写）**：添加参考视频 → 任务类型选「视频延长」→ 提示词写 延长 / 续写 / 延续。
```
向后延长 @视频1，@图片1 的角色从天而降，画面保持同一风格
续写 @视频1 前 5 秒，保持构图与光影一致
```

**视频编辑**：添加参考视频 → 任务类型选「视频编辑」→ 提示词写 编辑 / 加上 / 删掉 / 替换。
```
@视频1 中加一些小动物，活跃画面
把 @视频1 的人物替换为 @图片1
删掉 @视频1 的背景音乐
```

**首尾帧**：添加两张图分别设为「首帧」「尾帧」。

> 编辑 / 延长 / 首尾帧任务会自动锁定 `ratio=adaptive`、`duration=-1`（智能时长），页面里已内置这些示例词条，点击即可填入提示词。

## 目录结构

```
video-studio/
├── app.py           # FastAPI 后端（接口 + 后台轮询）
├── ark_client.py    # 火山方舟 API 封装
├── config.py        # 配置加载
├── config.json      # ★ 配置文件（在这里填 API Key）
├── store.py         # 任务本地存储（JSON）
├── run.sh           # 启动脚本
├── static/          # 前端页面
│   ├── index.html
│   ├── style.css
│   └── app.js
└── data/
    ├── tasks.json   # 任务记录
    ├── videos/      # 下载的视频
    └── uploads/     # 上传的图片（任务缩略图）
```

## 说明

- 视频 URL 有效期 24 小时，本平台会在任务成功后立即下载到本地，避免过期
- 任务记录保存在 `data/tasks.json`，重启不丢失
- Seedance 2.0 mini 并发数为 1，多任务会排队依次生成
- 也支持用环境变量 `ARK_API_KEY` / `ARK_BASE_URL` 覆盖 config.json