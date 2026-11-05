# AIWork

长期 AI 内容工作空间。**输入进仓库，输出进 `out/`；`out/` 不进 git。**

## 目录

```text
AIWork/
├── README.md                 # 本文件
├── AGENTS.md                 # Agent 操作规则
├── skills/                   # 所有 Skill（opencode.json 的 skills.paths 指向这里）
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

渲染（作品根用 `CINE_ROOT`）：

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

## 约定

- 新 Skill 放 `skills/`；`opencode.json` 的 `skills.paths` 指向这里。
- 新开源项目放 `repos/`；重媒体已忽略，源码保留。
- 共享素材放 `resources/`；作品专属素材放 `projects/<work>/lessons/<lesson>/assets/`。
- 不在仓库里放 `docs/`、`scratch/`；资料放 `resources/references/`，临时文件放 `out/_tmp/`。
- 不提交密钥、`out/`、构建中间产物。
- `resources/references/` 里的重媒体（mp4/mov/wav）默认不进 git；需要版本化用 Git LFS。
- 详细 Agent 规则见 `AGENTS.md`。
