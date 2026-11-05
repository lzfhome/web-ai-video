# AIWork

长期 AI 内容工作空间。**输入进仓库，输出进 `out/`；`out/` 不进 git。**

## 目录

```text
AIWork/
├── AGENTS.md                 # 本文件：工作空间规则 + 总览
├── Process.md                # 代码架构变更记录
├── opencode.json             # skills.paths 指向 ./skills
├── skills/                   # 所有 Skill
├── repos/                    # 开源项目/参考源码（已 vendor）
├── resources/                # 字体、音乐、图片、风格、资料
│   ├── fonts/
│   ├── music/
│   ├── sfx/
│   ├── images/
│   ├── styles/
│   └── references/
├── workspaces/               # 引擎/生产线的专属工作区（车间）
│   └── vibe-knowledge/
│       ├── cine/             # 渲染引擎
│       ├── templates/        # 空白作品模板
│       ├── tools/            # 时间轴、TTS、建项目脚本
│       └── voice/
├── projects/                 # 一个作品一个目录
│   ├── benford/
│   └── sangetsuki/
├── tools/                    # 本地工具/应用
│   └── video-studio/         # Ark/Seedance 工作台
└── out/                      # 临时 + 成品，git 忽略
    ├── _tmp/
    └── <work>/<日期>_<版本>/
```

## 概念

| 层 | 位置 | 说明 |
|---|---|---|
| 车间 | `workspaces/<category>/` | 工作流 + 引擎 + 模板 + 工具，不含具体作品 |
| 模板 | `workspaces/<category>/templates/` | 空白作品脚手架 |
| 作品 | `projects/<work>/` | 具体作品的源码、素材、设计 |
| 临时 | `out/_tmp/<work>/` | frames/audio/stills/picture/logs |
| 成品 | `out/<work>/<日期>_<版本>/` | video/cover/post/notes |

## 当前作品

- **本福特定律**：`projects/benford/` → `out/benford/2026-11-03_60s/`
- **山月记**：`projects/sangetsuki/`
  - 文字压图连续版（当前）：`lessons/006-text-on-image/` → `out/sangetsuki/2026-11-04_text-on-image/`
  - 混合静帧版：`lessons/004-hybrid-stills/`
  - 混合 Seedance 版：`lessons/005-hybrid-seedance/`
  - 默片字卡版：`lessons/003-silent-79s/`
  - 水墨纸本版：`lessons/002-paper/`

## 核心规则

1. **输入进仓库，输出进 `out/`。**
2. **`out/` 全部 git 忽略**：临时文件 + 成品都放这里。
3. **不在仓库里新建 `docs/`、`scratch/`。** 资料放 `resources/references/`，临时文件放 `out/_tmp/`。
4. **不提交密钥、`out/`、构建中间产物、大媒体。**
5. **作品优先**：一个作品一个 `projects/<slug>/`。

## 快速开始

新建一个作品：

```bash
python3 workspaces/vibe-knowledge/tools/new_project.py my-film --title "我的片子"
```

编辑：

```text
projects/my-film/lessons/my-film/narration.json
projects/my-film/lessons/my-film/film.js
projects/my-film/lessons/my-film/assets/
```

渲染：

```bash
CINE_ROOT=projects/my-film python3 workspaces/vibe-knowledge/cine/tools/record.py my-film --fps 30
CINE_ROOT=projects/my-film python3 workspaces/vibe-knowledge/cine/tools/finish.py my-film --fps 30
```

成品复制到：

```text
out/my-film/<日期>_<版本>/
├── video.mp4
├── cover.jpg
├── post.txt
└── notes.md
```

## 新增 Skill

```bash
# 放到 skills/<name>/SKILL.md
# opencode.json 的 skills.paths 指向 AIWork/skills，重启后自动发现
opencode debug skill
```

## 新增开源项目

放到 `repos/<name>/`。如果带 `.git`，先移除嵌套 `.git` 再 vendor，或明确改用 submodule；在 `repos/SOURCES.md` 记录 URL / commit / license。

## 新增作品

```bash
python3 workspaces/vibe-knowledge/tools/new_project.py <slug> --title "标题"
```

生成：

```text
projects/<slug>/
├── project.json
├── cine -> ../../workspaces/vibe-knowledge/cine
├── lessons/<slug>/
│   ├── narration.json
│   ├── film.js
│   ├── facts.md
│   └── assets/
└── design/
out/_tmp/<slug>/{build,stills}
```

编辑 `lessons/<slug>/narration.json`、`film.js`、`assets/`。

## 渲染

作品根通过 `CINE_ROOT` 指定：

```bash
CINE_ROOT=projects/<slug> python3 workspaces/vibe-knowledge/cine/tools/record.py <slug> --fps 30
CINE_ROOT=projects/<slug> python3 workspaces/vibe-knowledge/cine/tools/finish.py <slug> --fps 30
```

- `record.py` 输出 `lessons/<slug>/build/picture.mp4`，`build` 是软链，实际落在 `out/_tmp/<slug>/build/`。
- `finish.py` 输出 `lessons/<slug>/build/lesson<slug>.mp4`。
- 成品复制到 `out/<work>/<date>_<ver>/`，不要留在 `projects/`。
- 无旁白字卡视频可用 `workspaces/vibe-knowledge/tools/silent_timings.py`。
- edge-tts 对齐用 `workspaces/vibe-knowledge/tools/edge_tts_timings.py`。

## 素材

- 共享图/音乐/字体/风格：`resources/`。
- 作品专属：`projects/<work>/lessons/<lesson>/assets/`。
- AI 生成图/视频：用 `skills/vibe-knowledge/tools/ark_media.py`（默认 dry-run，确认后 `--yes`）。
- 生成画面默认带「AI 示意图 / AI 生成画面」角标。

## 架构变更记录

**改代码架构必须更新 `Process.md`；只改内容/文案/风格参数不写。**

`Process.md` 记录：

- 目录结构、模块边界、文件放置规则
- 引擎/渲染管线/路径契约（`CINE_ROOT`、`build`/`stills` 软链、`out` 布局）
- 配置加载、Skill 加载、`opencode.json`
- 依赖、构建方式、数据模型/API
- 迁移/兼容性变化

不记录：选题、文案、旁白、字卡内容、风格参数、单个作品素材、临时调试。

## Git

- `out/`、`**/build/`、`**/stills/`、`**/frames/`、venv、node_modules、密钥全部忽略。
- 大媒体放 `out/` 或 `resources/`；上游 `repos/` 和 `resources/references/` 的重媒体默认忽略，需要版本化用 Git LFS。
- 不主动 commit；用户明确要求再提交。

## 成品命名

```text
out/<work>/<YYYY-MM-DD>_<slug>/
├── video.mp4
├── cover.jpg
├── post.txt
└── notes.md
```
