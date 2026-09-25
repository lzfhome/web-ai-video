# OpencodeRecord · AIWork

> 本文件的用途：**记录所有 AI 协作会话的关键历史**——做了什么、怎么做、为什么做。
> 目的是把 `AIWork` 变成 git 仓库推到 GitHub 后，在**家里/别的机器** `git pull` 下来，
> 用这份 md 让 opencode 快速恢复上下文；在家里的改动继续 push 上来，当前机器也能同步接续。
> 规则：**每次会话的重要进展都要追加记录**；记录要详细（目标/做法/原因/文件/命令/结果）。

---

## 0. 仓库与总览

- 仓库根：`/home/oliver/workspace/AIWork/`
- 子项目：
  - `video-studio/` —— **视频/图片生成工作台**（FastAPI 后端 + 原生前端），本会话主要工作对象
  - `ai-learning/` —— 学习资料（分镜/运镜/导演 Skill/案例），含 `lzf/内容分镜学习/基础案例/*`（案例总结）
  - `kun/` —— 坤坤篮球案例（11 张图 + 重写后的 Readme.md 分镜提示词）
- 当前默认会话模型：`opencode-go/deepseek-v4-flash`

### 技术栈
- 后端：Python + FastAPI + uvicorn + pydantic + httpx（调火山方舟 Ark API）
- 存储：本地 JSON（`data/tasks.json`、`chain_jobs.json`、`extend_jobs.json`、`image_jobs.json`）+ 文件（`data/videos/`、`data/uploads/`）
- 前端：原生 HTML/CSS/JS（无框架），localStorage 做设置/素材/提示词持久化
- 外部依赖：`ffmpeg` / `ffprobe`（已装，用于截取/抽帧）、Ark 各模型 API

---

## 1. 项目目标（用户要什么）

做一个类似「即梦」的**本地 Web 视频生成工作台**：
- 视频生成（Seedance mini/fast/2.0/2.5）+ 图片生成（Seedream 5.0 pro/lite）
- 批量多图生成 + **尾帧衔接**（前段尾帧接下段首帧，长剧情连续）
- **长片延长**（extend：参考视频续写/多轮延长）
- **AI 分镜配图**（接口保留，聊天 UI 已移除）
- **图片生成后台化**（和视频一样在资产页异步跑，不阻塞界面）

### 用户明确偏好（务必遵守）
1. **不要聊天框**（AI 对话用户用本地 agent，app 里只做直填生成）
2. **不弹确认框**，点「✦ 生成」直接提交
3. 中间一个大文本框；**多行多图自动分到每张图描述**；「✓ 应用为分镜」按钮保留
4. 每张图有独立**时长输入框**（时长自己填，不写在文本里）
5. 刷新后保留：设置、素材、提示词、**当前标签页**
6. 图片模式/视频模式共用同一文本框
7. 操作要**可取消/多选/分类清晰**（资产分类、图片多选加入素材等）

---

## 2. 关键配置（video-studio/config.json）

- `api_key`（方舟 Ark key，勿外泄）、`ak`/`sk`、`usage_apikey_id`（用量查询）
- `default_model` = `doubao-seedance-2-0-mini-260615`
- `story_model` = `deepseek-v4-1-flash-260910`（AI 分镜对话模型）
- `image_model` = `doubao-seedream-5-0-260128`
- `models` / `image_models`：下拉预设（含中文名）
- `model_caps`：每个视频模型的能力配置（resolutions / max_duration / inputs / task_types / roles / camera_fixed / max_media / features）——**能力页、界面显隐全部由它驱动**
- `public_base_url`：本地上传视频需公网隧道才能被方舟访问（否则填公网 URL）

### 视频模型能力对照（来自 config.model_caps，2026-09）
| 能力 | mini | fast | 2.0 | 2.5 |
|---|---|---|---|---|
| 分辨率 | 480/720p | 480/720p | 480~4k | 480~1080p |
| 单段时长 | 4-15s | 4-15s | 4-15s | 4-30s |
| 输入 | 文本/图片 | 文本/图片 | 文本/图/视频/音频 | 全模态(50素材) |
| 首帧/尾帧/参考图 | 仅首帧 | 首尾帧+参考图 | ✓ | ✓ |
| 任务类型 | auto | auto | auto/文/图/编辑/延长 | 同2.0+多轮延长 |
| 画面运动 | 固定 | 固定 | 可运动 | 可运动 |
| @图片N/@视频N 引用 | ✗ | ✗ | ✓ | ✓ |
| R2V 分镜脚本参考 | ✗ | ✗ | ✓ | ✓ |
| 组图/批量/素材上限 | 10 | 10 | 20 | 50 |

> 注：2.0/2.5 用户账号需在方舟控制台**开通**（曾报 ModelNotOpen）。

### Ark API 硬限制（踩过的坑）
- **首帧/尾帧不能与参考图混用** → 尾帧衔接用「上一段尾帧作首帧 + 当前图作尾帧」实现
- **参考视频只收公网 URL**（local:// 需 public_base_url 隧道）
- 时长必须是 `-1`(智能) 或 `4~15/30`；**mini i2v 最短 4 秒**（填 2/3 会 400）
- **Seedream 图片尺寸必须 ≥ 3,686,400 像素**（≈2560×1440；1024×1024 会被 400 拒）
- 内容审核：战争/历史题材 + 真人肖像高概率拦截（详见 §7 架空化）

---

## 3. 会话时间线（本会话全部关键点）

### 3.1 平台搭建与打磨
- **目标**：从零搭起完整工作台。已完成的模块：API 客户端、任务存储、批量任务（尾帧衔接）、长片延长任务、图片生成（后台化）、用量/余额查询、资产卡片墙、设置/素材/提示词持久化、标签页持久化。
- **做法/原因**：
  - 聊天区移除（用户用本地 agent）；中间改大文本框 + 「✓ 应用为分镜」+「✦ 生成」
  - 确认弹窗移除：prepareSingle/Batch/Extend/Image 直接调 submit*
  - 图片生成改**后台任务**（ImageJobStore + `_process_images`），界面不转圈，进度显示在资产页
  - 静态文件加 no-cache 中间件；**改代码后需升版本号 `?v=N`**（否则浏览器缓存旧 JS，这是反复出现的坑）

### 3.2 关键 bug 与修复（重要教训）
1. **图片生图无反应** → 浏览器缓存旧 JS（强刷 + 升版本号解决）
2. **生图一直 0 张** → Seedream 尺寸低于 3,686,400 像素 → 尺寸下拉全换成达标大尺寸
3. **图片任务卡在 queued 挡住新提交** → 清理死代码时**误删 `_process_images` 定义** → 补回 + 外层 try/except 兜底 + 提交时自动中断超 3 分钟卡死任务
4. **移动资源默认目录** → 原生 showDirectoryPicker 无法指定起始目录 → 改**服务端文件夹浏览器**（默认打开 `ai-learning/lzf`，可上下浏览，移动限制在 `ai-learning` 内防误删）
5. **抽帧图片无法查看** → ffmpeg 输出到子目录，URL 对不上 → 改扁平化存 `data/uploads/{id}_%03d.jpg`，并修复旧记录
6. **分类错乱**：架空戏班提示词含「抽毒药」被误判为抽帧 → 后端给任务打 `kind`(gen/frame)，前端优先用 kind
7. **图片加入素材一次全加** → 改为**每张图可勾选多选**，只加选中的
8. **「AI生成图片」筛选为空** → 卡片标记是 gen/frame 但按钮值 img，映射不匹配 → 修 applyAssetFilter

### 3.3 功能清单（当前都有）
- 标签页：创作 / 资产 / 用量 / **能力**
- 创作页：模型下拉（能力自动适配显隐）、任务类型、生成参数（分辨率/比例/时长/seed/画面运动/声音/水印）、图片模式（组图开关/水印/尺寸含分辨率标注）、长片延长面板、直填大文本框
- 资产页：
  - **分类筛选**：全部 / 🎬AI生成视频 / ✂剪辑视频 / 🖼AI生成图片 / 🎞抽帧图片（记住选择）
  - 视频卡片：内嵌播放/下载/📦移动/✂截取/删除 + **本地位置标注**（📍data/videos/…、📦已移动→路径、☁云端）
  - 图片任务卡片：进度条、停止/删除、**多选勾选加入素材**、📦移动、点击放大(lighbox)
  - 移动资源 = **服务端文件夹浏览器**，默认 `ai-learning/lzf`，真剪切
  - 截取弹窗：输出类型=视频片段/帧图；截取位置=开头/结尾；视频片段=该段视频；帧图=**前N帧/后N帧**（或填区间 `2-4` 均匀抽帧），帧图默认 10s 窗口曾误改，最终改回「按用户选择，不做默认」
- 能力页：视频模型对照表（动态读 config）+ Seedream pro/lite 对照表 + 模型列表
- 顶部头像：localStorage 持久化，菜单可「用作素材」

### 3.4 案例与提示词
- **案例5 篮球**：文生图 4×4 网格（16 步动作+箭头）→ mini 图生视频 15s。总结在 `ai-learning/lzf/内容分镜学习/基础案例/1/Readme.md`
- **超 15s 的做法**：拆成多张网格图 → 多段 ≤15s 视频 → **首尾帧衔接** → ffmpeg 拼接（段段重叠 1 个动作保连续）
- **架空化改写**（过审核）：民国抗战→架空王朝、日军→权贵/宾客，加「全虚构人物与剧情，不涉及真实人物/历史事件」声明。已写入 `story_prompts.json`（9 条）和 `single_prompts.json`（9 分镜整版）；原坤坤版备份 `story_prompts.kun.bak.json` / `single_prompts.kun.bak.json`
- **单图模板载入**：左侧「📖 载入模板(single_prompts)」弹窗选择填入主框；多图模式仍是「载入 story_prompts」
- `single_prompts.json` 曾因未转义换行非法 JSON → 修复为 `\n` 转义

### 3.5 镜头语言学习（用户问题）
景别（远/全/中/近/特）· 角度（平/俯/仰）· 运动（推/拉/摇/移/跟/升降/环绕/手持）。学习方法：拉片记录「景别+角度+运动」→ 在 AI 里同提示词换镜头对比。

### 3.6 ComfyUI / 工作流咨询
- 用户只调付费 API → 装 **ComfyUI Desktop（NVIDIA 版）** 在 Win VM 上跑 API 编排即可（本地不吃 GPU）
- 付费 API 路线工具搭配：即梦官网(灵感) → 本工作台(批量/衔接) → 剪映(成片) → 发布
- Seedance 2.0 官方能力：多模态全参考(9图+3视频+3音频)、R2V 分镜、编辑/延长、双声道

---

## 4. 常用命令（运维手册）

### 启动 / 停止
```bash
# 启动（后台，日志到 /tmp/opencode/vsXXX.log）
cd /home/oliver/workspace/AIWork/video-studio
setsid nohup uvicorn app:app --host 0.0.0.0 --port 8000 > /tmp/opencode/vsXXX.log 2>&1 < /dev/null & disown

# 停止（[ ] 防 pkill 自匹配挂起，务必用这个写法）
pkill -9 -f "uvicorn[ ]app:app"
```

### 改前端后
- 静态文件已 no-cache；**改了 app.js/style.css 后把 index.html 里的 `?v=N` 升一版**，并让用户 `Ctrl+Shift+R` 强刷

### 语法检查
```bash
node --check static/app.js
python3 -c "import ast; ast.parse(open('app.py').read())"
```

### 测试接口
```bash
curl -s http://127.0.0.1:8000/api/tasks | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/genjobs
curl -s "http://127.0.0.1:8000/api/fs/browse"
```

---

## 5. 后端接口速查（video-studio/app.py）

- `GET /api/config` —— 配置 + model_caps（前端 CFG 来源）
- `POST /api/tasks` · `GET /api/tasks` · `POST /api/tasks/{id}/stop` · `DELETE /api/tasks/{id}`
- `POST /api/chain` · `GET /api/chain` · `/api/chain/{id}/stop`（批量+尾帧衔接）
- `POST /api/extendjob` · `GET /api/extendjobs`（长片延长）
- `POST /api/genjob` · `GET /api/genjobs` · `/api/genjobs/{id}/stop|DELETE`（图片后台任务，job 带 `kind`）
- `POST /api/move` · `GET /api/move-roots` · `GET /api/fs/browse`（移动/文件夹浏览，限 ai-learning 内）
- `POST /api/cut`（ffmpeg 截取片段）· `POST /api/frames`（ffmpeg 抽帧：前N/后N 或区间）
- `GET /api/story_prompts` · `GET /api/single_prompts`
- `GET /api/usage?days=7` · `GET /api/balance`
- `GET /api/videos/{name}` · `GET /api/uploads/{name}` · `POST /api/upload` · `POST /api/upload_image`

---

## 6. 恢复会话的方法（家里用）

1. `git clone` 你的 AIWork 仓库
2. 安装依赖：`pip install fastapi uvicorn pydantic httpx python-multipart`
3. 打开 opencode 指向 `AIWork/`，告诉它「读 `OpencodeRecord.md` 恢复上下文」
4. 启动服务：见 §4 命令（Windows 用 `uvicorn app:app --host 0.0.0.0 --port 8000` 前台跑）
5. 在家里的改动继续提交 push；回来后 `git pull` + 看本文件新增记录即可接续

---

## 7. 坑位清单（踩过就要记住）

- **浏览器缓存**：改 JS/CSS 必须升 `?v=` + 强刷
- **Ark 审核**：战争/历史/真人肖像高概率拦截 → 架空化 + 「全虚构」声明
- **Seedream 尺寸下限** 3,686,400 像素
- **mini 时长** 4~15s，i2v 最短 4s
- **首尾帧 ≠ 参考图** 不能混用
- **参考视频** 需公网 URL
- **JSON 文件** 写多行提示词必须转义 `\n`
- **删死代码前先 grep 引用**（曾误删 `_process_images` 导致任务卡死）
- **分类逻辑用显式标记**（kind），别用内容匹配（会被「抽毒药」之类误伤）

---

## 8. 下一步建议 / 待办（供后续会话延续）

- 2.0/2.5 待用户在方舟控制台开通（开通后工作台直接切模型即可用全部能力）
- 可加：一段式「分镜→自动出图→自动逐段图生视频→ffmpeg 拼接」一键全流程
- 可加：失败任务一键重试
- 可加：`run.bat`（Windows 启动脚本）
- Seedream 参考图上限（pro 多图参考吃几张）待实测确认后可在 UI 加提示

---

## 9. 后续会话追加记录（2026-09-24）

### 9.1 磁盘资源分类（重要）
用户要求资产按四分类在磁盘上分文件夹，与资产页筛选一一对应：
```
data/
├── gen_videos/   🎬 AI 生成视频
├── cut_videos/   ✂ 剪辑视频
├── gen_images/   🖼 AI 生成图片
├── frames/       🎞 抽帧图片
└── refs/         用户上传素材（支撑目录）
```
- 后端常量：`V_AI_DIR/V_CUT_DIR/UP_IMG_DIR/UP_FRAME_DIR/UP_REF_DIR` 指向上述目录
- 解析器 `_video_path` / `_upload_path` 兼容新旧路径（含 `uploads/` 遗留）
- 图片任务结果文件名带前缀 `gen_images/`、`frames/`；上传返回 `refs/`；URL 走 `/api/uploads/{path}`(:path 路由)
- 已迁移现有文件并更新 `tasks.json`(local_video/image_path) 与 `image_jobs.json`(results)

### 9.2 删除本地文件
- `DELETE /api/tasks/{id}`：删任务记录 + 本地视频(image_path/local_video)
- `DELETE /api/genjobs/{id}`：**也删结果图片文件**（新增）
- 资产页点 X 即删本地文件

### 9.3 废弃资源清理 + 教训
- 脚本按「tasks + image_jobs 引用」求孤儿文件并删除（一次清掉 101.8MB 孤儿，主要 refs 上传素材）
- **教训**：迁移时把 `image_path` 存成相对路径 → 清理脚本按相对解析对不上 → **误删 5 张被引用的缩略图**。修复：`image_path` 一律存绝对路径；清理前先反向校验「被引用但文件缺失」。缩略图丢失不影响视频本体。

### 9.4 后端错误排查
- 502 排查：POST /api/tasks 失败会 `print("[create_task 失败] ...")` 到日志，方便定位
- 案例：`InputImageSensitiveContentDetected.PolicyViolation` = 输入图片（首帧/参考图）被方舟审核判定涉及版权/肖像 → 换图或实名授权，非代码问题

### 9.5 本会话其他
- OpencodeRecord.md 本文件本身：用户要求随仓库同步，作为跨机器恢复会话的入口（clone→读 md→启动）
- 待办补充：git 化（.gitignore 排除 data/ 大文件）尚未做，用户问过两次

---

## 10. Git 化与仓库同步（2026-09-24 后续）

### 10.1 磁盘四分类最终结构（用户拍板）
```
video-studio/data/
├── gen_videos/   🎬 AI 生成视频
├── cut_videos/   ✂ 剪辑视频
├── gen_images/   🖼 AI 生成图片
├── cut_frames/   🎞 抽帧图片（原 frames 改名 cut_frames）
└── refs/         用户上传素材
```
- 已删除遗留空目录 `uploads/`、`videos/`；`_save_data_image` 改存 `refs/`
- 后端 `_video_path`/`_upload_path` 兼容旧路径

### 10.2 提示词记录
- `data/prompts.jsonl`（追加式，每行 JSON：`{time, kind, model, prompt, ref}`）
- 四类提交都记录：video / image / chain / extend（在 create 成功后调用 `_log_prompt`）

### 10.3 配置与密钥拆分（重要，安全）
- `config.json`：只存非敏感配置（models/model_caps/defaults 等），**入库**
- `config.secrets.json`：6 个密钥字段（api_key/base_url/public_base_url/access_key_id/secret_access_key/usage_apikey_id），**不入库**（gitignore）
- `config.py`：加载 config.json 后用 config.secrets.json 覆盖密钥；环境变量 `ARK_API_KEY`/`ARK_BASE_URL` 仍可覆盖
- 已删除 `config.example.json`（用户要求），git 历史中无密钥/example/bak 文件

### 10.4 Git 仓库与推送
- 仓库：`git@github.com:lzfhome/web-ai-video.git`（**https://github.com/lzfhome/web-ai-video**）
- `.gitignore` 排除：`config.secrets.json`、`data/`、`*.bak.json`、`*.mp4/*.mov/*.wav`（教学视频超 GitHub 100MB 限制）、`.sid`、`__pycache__`
- 教训：`ai-learning/故事板10套案例/` 里 10 个教学视频（最大 127MB）曾把 `.git` 撑到 460M → 用 `git rm --cached '*.mp4'` + 重写提交 + `git gc` 清理到 92M 后推送成功
- 路径带引号（core.quotepath）导致 `git rm $(git ls-files | rg ...)` 失败 → 用 pathspec 通配 `git rm --cached '*.mp4'` 解决
- 已推送 2 次：初始全量（main）+ 案例2 Readme.md

### 10.5 案例2（用户自己总结）
- `ai-learning/lzf/内容分镜学习/基础案例/2/Readme.md`：mini 尽量延长视频的分段衔接思路（Seedream→4×4 图→Seedance→取尾帧→进入第二段+多张角色/服装参考图）

### 10.6 家里恢复运行步骤（重要）
```
git clone git@github.com:lzfhome/web-ai-video.git
cd web-ai-video/video-studio
pip install fastapi uvicorn pydantic httpx python-multipart
# 创建 config.secrets.json 填入密钥（参照本机该文件格式）
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 10.7 run.sh 行为（用户要求）
- **缺失 `config.secrets.json` 时：打印创建指引（字段模板 + 获取地址）并 `exit 1`，不再照常启动**
- 有密钥文件才正常启动；`chmod +x run.sh` 后 `./run.sh` 即可
- 已推送 `ed0aa4e`

---

## 11. Windows 机器恢复运行（2026-09-25 追加）

### 11.1 环境搭建（这台 Windows 机器）
- 仓库位置：`D:\AIWork\web-ai-video`（全新 clone，完整历史已拉取 `git fetch --unshallow`）
- Python：**3.12.10**，安装在 `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`
  - 安装方式：`winget install Python.Python.3.12 -e`
  - 依赖：`pip install fastapi uvicorn pydantic httpx python-multipart`（版本：fastapi 0.141 / uvicorn 0.54 / pydantic 2.13 / httpx 0.28 / python-multipart 0.0.32）
- ffmpeg：`winget install Gyan.FFmpeg -e`（截取/抽帧依赖；安装较慢，需耐心等）

### 11.2 密钥
- `config.secrets.json` 已创建并填入真实密钥（已被 `.gitignore` 忽略，不入库）
- 验证：`GET /api/balance` 返回余额 **¥98.94**（AccountID 2132091834）→ 密钥有效

### 11.3 Windows 启动命令
```powershell
cd D:\AIWork\web-ai-video\video-studio
# 前台运行：
%LOCALAPPDATA%\Programs\Python\Python312\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8000
```
- 访问：`http://localhost:8000`
- 验证接口：`GET /api/config`（默认模型 `doubao-seedance-2-0-mini-260615`）

### 11.4 本机器网络备注（故障排查背景）
- 该 Windows 机器之前的"假连接"问题：Anycast VPN 隧道卡死（界面显示已连接但流量不通，DNS 通过但 HTTP 全超时）。
- 修复方法：重启 `AnycastService` + 客户端手动重新连接；已做桌面一键修复脚本 `修复Anycast网络.bat`。
- 教训：批处理脚本必须 **GBK 编码 + CRLF 换行**（cmd 不认 UTF-8/LF，会撕碎命令）。

---

## 12. Windows 首日排障与运行验证（2026-09-25 追加2）

### 12.1 ffmpeg 安装（国内镜像方案）
- 直接 gyan.dev 走墙外源（约 190KB/s，VPN 断后仅 13KB/s）**不可用**；winget 的 Gyan.FFmpeg 走 GitHub 也卡死。
- **最优解：国内 GitHub 加速镜像 + 断点续传**。实测直连（VPN 断）：
  | 源 | 速度 |
  |---|---|
  | gh-proxy.com | **2.3~19.7 MB/s** ✅ |
  | ghfast.top | 140 KB/s |
  | ghproxy.net | 18 KB/s |
  | mirror.ghproxy.com | 不通 |
- 命令：`curl -L -o ffmpeg-essentials.zip "https://gh-proxy.com/https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip"`（109MB，10 秒下完）
- 解压到 `D:\AIWork\ffmpeg\ffmpeg-9.0.2-essentials_build\bin`，并加入**用户 PATH**。
- **教训**：国外源挂 VPN、国内源断 VPN；别在同一个网络状态下折腾两者。

### 12.2 ffmpeg 9.x 兼容性修复（重要坑，新机器必改）
- 现象：抽帧接口报 `Unrecognized option 'vsync'`。
- 原因：`app.py:1246` 用了旧版 ffmpeg 的 `-vsync 0`，**ffmpeg 9.x 已移除 `-vsync`**，替换为 `-fps_mode`。
- 修复：`"-vsync", "0"` → `"-fps_mode", "passthrough"`，重启 uvicorn 后 `/api/frames` 验证通过（4 帧落盘 `data/cut_frames/`）。

### 12.3 「生成卡在提交」根因（关键）
- 现象：点「✦ 生成」后一直卡在提交（最长 120s 超时，有的调用 `timeout=None` 永不超时）。
- **根因：Anycast 智能分流把方舟 API（`volces.com`，.com 域名）误判为走代理**——分流规则只有 `domainSuffix:["cn"]` 直连，.com 不命中，只能靠 IP 地理库，结果被送进隧道。
- 证据：`netstat` 看到 uvicorn 到方舟(101.126.7.76:443)的连接 source 是 TUN 虚拟 IP `10.255.254.2`。
- 测速：走隧道 4.6s；**断开 VPN 直连 1.4s**；提交任务走隧道疑似卡死、直连 1.8s 成功。
- **结论/操作习惯：用工作台（方舟是国内 API）时断开 Anycast；push GitHub 时再挂 VPN。**

### 12.4 其他
- 测试任务 `cgt-20260925224309-k6rb6`（苹果旋转 5s）与用户已生成 `cgt-20260925224501-dscdj.mp4`、`gen_images/8f9eda817cdb37e4.jpg` 均正常；抽帧功能用用户视频实测通过。
- uvicorn 重启注意：**必须从注入了新 PATH 的进程启动**（Start-Process 继承调用方环境），否则新进程仍找不到 ffmpeg。