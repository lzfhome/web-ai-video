# AIWork Agent Rules

## 核心原则

1. **输入进仓库，输出进 `out/`。**
2. **`out/` 全部 git 忽略**：临时文件 + 成品都放这里。
3. **不在仓库里新建 `docs/`、`scratch/`。** 资料放 `resources/references/`，临时文件放 `out/_tmp/`。
4. **不提交密钥、`out/`、构建中间产物、大媒体。**
5. 作品优先：一个作品一个 `projects/<slug>/`。

## 目录约定

```text
skills/                  # Skill，opencode.json 的 skills.paths 指向这里
repos/                   # 开源项目/参考源码（已 vendor）
resources/               # 共享字体、音乐、图片、风格、资料
workspaces/<category>/   # 车间：引擎 + 模板 + 工具，不放具体作品
projects/<work>/         # 作品：project.json + lessons/ + design/
out/_tmp/<work>/         # 临时：frames/audio/stills/picture/logs
out/<work>/<date>_<ver>/ # 成品：video/cover/post/notes
tools/                   # 本地工具/应用（video-studio 等）
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
