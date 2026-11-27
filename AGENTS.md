# AIWork

长期 AI 内容工作空间。**原料进 `resources/`，引擎进 `cine/`，产线进 `line/`，产物进 `projects/`。**

> 文档跟着目录走：每条 `line/<name>/`、每个 `cine/` 子目录都有自己的 `AGENTS.md`。新会话先看对应目录的 `AGENTS.md`，再看本文件的规则。上游 `repos/`、`tools/local/`、`resources/references/` 保持原样，不改名。

## 目录

```text
AIWork/
├── AGENTS.md                 # 本文件：工作空间规则 + 总览
├── project.py                # 根目录统一项目入口（所有 workspace）
├── Process.md                # 代码架构变更记录
├── opencode.json             # skills.paths 指向 ./skills
├── skills/                   # 方法论、提示词、Skill 文档
├── repos/                    # 开源项目/参考源码（已 vendor）
├── resources/                # 全车间共享原料
│   ├── fonts/
│   ├── music/
│   ├── sfx/
│   ├── images/
│   ├── styles/
│   ├── voice/
│   └── references/
├── cine/                     # 共享合成引擎
│   ├── audio/                # 配音 / BGM / 音效 / 混音
│   ├── video/
│   │   ├── engines/dom/      # DOM/CSS + Three.js 引擎 + 录制工具
│   │   └── engines/canvas/   # Canvas + WebCodecs 快速通道
│   ├── image/                # Ark / Seedream / Seedance 素材引擎
│   ├── media/                # B 站视频/音频下载（yutto）
│   └── vendor/               # three.js 等引擎依赖
├── learning/                 # 自己的学习笔记（md）
├── learning-downloads/       # 下载的大容量学习资料，git 忽略
├── workspaces/
│   └── vibe-knowledge/       # 知识短片车间
│       ├── line/             # 产线型号
│       │   ├── canvas-bgm/   # Canvas + BGM-only
│       │   ├── dom-narrated/ # DOM + 旁白 + BGM
│       │   ├── poetry/       # 书封决定背景 + 诗句卡片 + BGM
│       │   └── poetry-tts/   # 同上 + 豆包配音（时长跟着配音走）
│       └── projects/         # 产物（源码 + build + deliveries），不进 git
└── tools/                    # 本地工具 / 共享基础设施
    ├── lib/                  # paths / ffmpeg / browser / server / scaffold
    ├── doctor.py
    ├── smoke_test.py
    ├── prune_tmp.py
    ├── video-studio/         # Ark/Seedance 工作台
    └── local/                # Node 22 / ffmpeg / npm 缓存，git 忽略
```

## 概念

| 层 | 位置 | 说明 |
|---|---|---|
| 原料 | `resources/` | 字体、音乐、音效、风格、参考，所有车间共用 |
| 引擎 | `cine/audio` `cine/video` `cine/image` `cine/media` | 可复用的合成 / 取素材能力 |
| 产线 | `workspaces/<产品>/line/<型号>/` | 选引擎、定流程，直接生产 |
| 产物 | `workspaces/<产品>/projects/<work>/` | 源码、素材、build、deliveries，整目录不进 git |
| 工具 | `tools/` | CLI、本地应用、工具链 |

## 当前作品

- **天空为什么是蓝的？**（`canvas-bgm`）：`workspaces/vibe-knowledge/projects/sky-blue/`
- **本福特定律**（`dom-narrated`）：`workspaces/vibe-knowledge/projects/benford/`
- **山月记**（`dom-narrated`）：`workspaces/vibe-knowledge/projects/sangetsuki/`
  - 文字压图连续版：`lessons/006-text-on-image/`
  - 混合静帧版：`lessons/004-hybrid-stills/`
  - 混合 Seedance 版：`lessons/005-hybrid-seedance/`
  - 默片字卡版：`lessons/003-silent-79s/`
  - 水墨纸本版：`lessons/002-paper/`

## 核心规则

1. **原料不进引擎，引擎不进作品，作品不进 git。**
2. `resources/` 是唯一原料池；不要再往 skill / cine 里复制字体、BGM、风格图。
3. `cine/` 只放合成能力，不放某个作品的业务脚本。
4. `line/` 只放产线型号；新的产品流程加在这里。
5. `projects/` 整个目录 git 忽略（源码 + build + 成品都在里面）。
6. 不新建 `out/`、`docs/`、`scratch/`；临时文件放对应项目的 `build/`。
7. **仓库根目录只允许这 8 个文件**：`AGENTS.md`、`Process.md`、`project.py`、`requirements.txt`、`opencode.json`、`opencode.list`、`.gitignore`、`.gitattributes`（以及 `.git/`、`.opencode/`、`__pycache__/`、`cine/`、`learning/`、`learning-downloads/`、`repos/`、`resources/`、`skills/`、`tools/`、`workspaces/` 目录）。
   抓网页、下封面、试音乐、做预览页产生的 `.html` / `.json` / `.jpg` / `.mp3` 一律写到**对应项目的 `build/`**，不要落在根目录，也不要放进 `tools/local/`。
8. 不提交密钥、`tools/local/`、`projects/`、构建中间产物、大媒体。
9. **`tools/local/` 只放工具和缓存**：不放具体作品/小说的截图、抓取脚本、素材、对比页；作品相关临时文件一律放该作品 `projects/<work>/build/`。
10. **选题先定主线，感情类内容 ≤50%**：每个题材先写一句主线；感情类**只指爱情/romance**（爱情、CP、告白、思念、吃醋、虐恋），按场次计（台词 + 旁白合计）最多 50%。**其余内容全部按主线判断**：兄弟情、亲情、家国、战斗、命运、成长、幽默都算主线，不计入感情比例。50% 是上限，不是目标。
11. **旁白 ≤50%**：按场次计，旁白最多一半，其余给台词；旁白比例和感情比例是两套账，不能互相抵扣。

## Agent 可执行标准（强制）

任何新增/修改的 `line`、`cine`、工具，都必须做到「换一个 Agent、不带本次会话记忆，也能直接跑」。做不到就不算完成。

1. 目录内必须有 `AGENTS.md`；会产出视频/图片的 line 还必须有一份 `TEMPLATE.md`。
2. `TEMPLATE.md` 必须写清：输入变量、目录契约、命令、依赖/环境、最小样例、校验、失败怎么处理。
3. 命令必须能从仓库根目录直接执行；不依赖会话里临时设置的环境变量、临时文件、手工改文件。
4. 数据与代码分离：作品目录只放内容、素材、build、deliveries；引擎和默认参数归 line 或 cine。
5. 每条 line 必须有一个最小样例输入 + 一条 smoke test，并保证它现在就能通过。
6. 文档必须和代码一致；没实现的能力标 `TODO`，不要写成已支持。
7. 只用 Markdown / JSON / CLI，不依赖某个 Agent 的私有 skill 或界面。
8. `cine/` 只放公共能力；某个产线专属的引擎和默认值放该 `line/`。

当前示例：`workspaces/vibe-knowledge/line/poetry/TEMPLATE.md`。

## 用户偏好（BGM / 素材）

- 用户所有成片均为**自用、不发布、不商用**。日常 BGM/素材获取不要再反复确认用途，也不要以“商用授权/版权风险”为由拒绝或劝退。
- 需要说明时只讲技术限制（平台 VIP/DRM、接口失效、文件大小），不要展开商业授权说教。
- 已确认的曲目、工具、路径直接复用：`resources/music/`、`tools/local/musicdl`、`cine/audio/tools/get_bgm.py`、`cine/audio/tools/musicdl_bgm.py`。
- 下载/转码/入库按 `cine/audio/AGENTS.md` 的「BGM 获取」流程直接做。

## 交互规则（强制）

1. **给用户 A/B/C 方案时，必须用可点击选项（`question` 工具），不要让用户再打字回复。** 推荐项放第一，并在标签末尾写“（推荐）”；每个选项给一句说明。
2. 需要用户确认、选择方向、选句子、选版本时，同样优先用可点击选项；只有选项无法枚举时，才用普通提问。
3. 用户不需要“给人看”的文档。AIWork 自有说明统一命名为 `AGENTS.md`，不再新建 `README.md`；`TEMPLATE.md`、`SOURCES.md` 这类硬规则文件保留原名。
4. 上游 `repos/`、`tools/local/`、`resources/references/` 里的 `README.md` 是第三方内容，保持原样，不改名、不改写。

## 快速开始

```bash
python project.py list
python tools/doctor.py
python tools/smoke_test.py     # 3 秒端到端冒烟，成功后自动清理
python tools/prune_tmp.py      # 查看 projects 里可清理多少；加 --yes 执行
```

新建作品就是复制产线骨架（**line 就是模板**）：

```powershell
# 看有哪些产线和骨架
python project.py lines vibe-knowledge

# 复制对应产线的 skeleton，改名去掉 .skeleton
# canvas-bgm: line/canvas-bgm/film.canvas.skeleton.js -> lessons/<project>/film.canvas.js
# dom-narrated: line/dom-narrated/film.skeleton.js -> lessons/<project>/film.js
```

poetry 例外：它的入口是 `line/poetry/build.json`，跑一次生成一个新项目。

```powershell
python project.py build poetry          # 读 build.json → 建项目 → 渲染 → 交付
```

每条 line 的用途、该改哪个文件、参数长什么样：看该 line 目录下的 `AGENTS.md`。

旁白母版从 `skills/vibe-knowledge/templates/narration/` 取；`project.json` 里写 `line`。

编辑：

```text
workspaces/vibe-knowledge/projects/my-film/
├── project.json
├── lessons/my-film/
│   ├── narration.json
│   ├── film.canvas.js   # canvas-bgm
│   ├── film.js          # dom-narrated
│   ├── poem.json        # poetry（版式/调色板/特效/时长）
│   ├── facts.md
│   ├── assets/
│   ├── build/           # 中间产物
│   └── stills/          # 接触表
└── deliveries/          # 成品
```

渲染：

```powershell
python project.py render my-film
python project.py render my-film --line canvas-bgm --fps 60
python project.py render my-film --line dom-narrated --workers 2
python project.py render my-film --line poetry --workers 2
python project.py deliver my-film --title "我的片子" --poster 12
python project.py qa my-film
```

底层脚本仍可直接调用：

```powershell
$env:CINE_ROOT="workspaces/vibe-knowledge/projects/my-film"
python cine/video/engines/dom/record.py my-film --fps 30
python workspaces/vibe-knowledge/line/dom-narrated/finish.py my-film --fps 30
python cine/video/engines/deliver.py my-film --title "我的片子" --poster 12
```

批量：项目根放 `queue.txt`，每行 `课号|标题|封面秒`：

```powershell
python cine/video/engines/queue.py my-film --workers 4
```

## Canvas 快速通道（BGM-only）

没有旁白、画面以文字/图形/图表为主时，用 Canvas 组件 + WebCodecs，30 秒片约 8–12 秒出片：

```powershell
python project.py render sky-blue --line canvas-bgm --fps 30
python project.py deliver sky-blue --title "片名" --poster 1
```

- 作品里的 `film.canvas.js` 导出 `duration / fps / images / build(c)`；组件在 `cine/video/engines/canvas/components.js`。
- 只支持 Canvas 能画的视觉；DOM/CSS 复杂的样式用 `dom-narrated`。

## 产线

每条 line 的目录下都有一份 `AGENTS.md`，写清楚它做什么、改哪个文件、参数怎么传。

| 产线 | 引擎 | 适用 |
|---|---|---|
| `canvas-bgm` | `cine/video/engines/canvas` + `cine/audio` | BGM-only、文字/图表/简单图形 |
| `dom-narrated` | `cine/video/engines/dom` + `cine/audio` | 旁白、复杂 DOM/CSS、46 套风格、片段叠加 |
| `poetry` | DOM/CSS + 书封/诗句 | 书封做背景，诗句代码排版，BGM |
| `poetry-tts` | poetry + `cine/audio/clients/doubao_tts.py` | 同上，但每场时长由豆包配音决定，文字跟着声音出 |
| `fe-gba` | `cine/image`（Seedream 帧图 + Seedance 2.5 flash） | GBA 火纹单镜头：原画参考 → 帧图 → 5–30s 视频 |

产线入口：`workspaces/vibe-knowledge/line/<型号>/render.py`；文档：同目录 `AGENTS.md`。

## 引擎

`cine/` 的每个子目录也有自己的 `AGENTS.md`：

| 目录 | 作用 |
|---|---|
| `cine/audio` | 配乐、音效、旁白时间轴、混音 |
| `cine/image` | Ark：Seedream 图 / Seedance 视频 |
| `cine/media` | B 站视频/音频下载（yutto）：封面 + meta.json |
| `cine/video` | 交付、批量队列、系列索引 |
| `cine/video/engines/dom` | DOM/CSS + Three.js 渲染引擎 |
| `cine/video/engines/canvas` | Canvas + WebCodecs 快速通道 |
| `cine/vendor` | three.js |

## 素材

- 共享字体/音乐/音效/风格/音色/参考：`resources/`。
- **`resources/` 的字体、音乐、音效、风格预览图、图片只留本地，不进 git**；A 按各目录的 `AGENTS.md` / `SOURCES.md` 重新准备。
- **下载的大容量学习资料统一放 `learning-downloads/`**（按主题建子目录），整目录不进 git；`learning/` 其他位置只放自己整理的 md 笔记。
- B 站参考视频：`python cine/media/engines/bilibili.py download BV...`，默认落 `resources/references/bilibili/<BV>/`（视频 + `cover.jpg` + `meta.json`）；未登录只有 480P，1080P+ 先跑 `login` 扫码。
- 作品专属素材：`projects/<work>/lessons/<lesson>/assets/`。
- AI 生成图/视频：`python cine/image/engines/ark.py image|video|assets ...`，默认 dry-run，确认后加 `--yes`。
- 生成画面默认带「AI 示意图 / AI 生成画面」角标。

## 新增 Skill / 开源项目

```bash
# Skill：skills/<name>/SKILL.md；opencode.json 的 skills.paths 指向 AIWork/skills
opencode debug skill
```

开源项目放 `repos/<name>/`。带 `.git` 的先移除嵌套 `.git` 再 vendor，或明确改用 submodule；在 `repos/SOURCES.md` 记录 URL / commit / license。

## 架构变更记录

**改代码架构必须更新 `Process.md`；只改内容/文案/风格参数不写。**

`Process.md` 记录目录结构、模块边界、路径契约（`CINE_ROOT`、`/cine/*` 映射、`projects` 布局）、配置/依赖、迁移与兼容性变化；不记录选题、文案、旁白、字卡内容、风格参数、单个作品素材、临时调试。

## Git

- `workspaces/vibe-knowledge/projects/`、`resources/` 中的重媒体、`tools/local/`、`**/build/`、`**/stills/`、venv、node_modules、密钥全部忽略。
- 大媒体放 `projects/` 或 `resources/`；上游 `repos/` 和 `resources/references/` 的重媒体默认忽略，需要版本化用 Git LFS。
- 不主动 commit；用户明确要求再提交。

## 成品命名

```text
workspaces/vibe-knowledge/projects/<work>/deliveries/<YYYY-MM-DD>_<slug>/
├── video.mp4
├── cover.jpg          # B 站封面，16:9
├── post.txt           # B 站投稿包
└── notes.md
```

### B 站投稿包（强制）

每条成片交付，除视频和封面外，必须同时生成 `post.txt`，至少包含：

1. **标题 2–3 个候选**：≤80 字，书名/作者可检索，推荐项放第一。
2. **简介**：≤2000 字，含时间轴、句子来源、免责声明；默认给“简洁 / 标准 / 情感”三版。
3. **标签**：≤10 个，前 8 个为内容标签。
4. **分区**：默认「知识 → 人文历史」，备选「知识 → 综合知识」。
5. **封面说明**：16:9，建议 1920×1080；写明底图、裁切和标题字。
6. **声明**：AI 生成画面标注、转载/版权说明、非商用说明。

没有 `post.txt` 不算交付。`deliver` 只出视频不算完成。
