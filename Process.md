# Process

记录 AIWork 的**代码架构变化**。只记架构，不记内容。

## 什么算架构变化

- 目录结构、模块边界、文件放置规则
- 引擎 / 渲染管线 / 路径契约（`CINE_ROOT`、`build` / `stills` 软链、`out` 布局）
- 配置加载、Skill 加载、`opencode.json`
- 依赖、构建方式、数据模型 / API
- 迁移 / 兼容性变化

## 什么不算

- 选题、文案、旁白、字卡内容
- 风格参数、颜色、字体、单个作品的 assets
- 临时调试、一次性的渲染参数

## 记录格式

新记录加在最上面：

```text
## YYYY-MM-DD · 标题

- 变更：
- 原因：
- 影响：
- 迁移：
- 相关 commit / files：
```

---

## 2026-11-05 · 项目优先工作空间重构

- **变更**：
  - 顶层改为 `skills / repos / resources / workspaces / projects / tools / out`。
  - 作品源码统一到 `projects/<work>/`；`workspaces/<category>/` 只放引擎、模板、工具。
  - 输出统一到 `out/`：`out/_tmp/<work>/` 放中间产物，`out/<work>/<日期>_<版本>/` 放成品；`out/` 全量 git 忽略。
  - `vibe-knowledge` 的 `cine` 引擎改为共享：`projects/<work>/cine` 软链到 `workspaces/vibe-knowledge/cine`。
  - `record.py` / `finish.py` / `clips.py` 的根路径改为 `CINE_ROOT`，不再假设脚本所在位置。
  - `lessons/<lesson>/build` 和 `stills` 改为软链，指向 `out/_tmp/<work>/`。
  - 新增 `workspaces/vibe-knowledge/tools/new_project.py`，按项目优先创建作品。
  - Skill 加载改为项目级 `opencode.json`：`skills.paths: ["./skills"]`；移除 `~/.claude/skills` 和 `~/.config/opencode/skills` 依赖。
  - `session-log` 从全局移入 `skills/session-log`。
  - 上游仓库 vendor 到 `repos/`（移除各自 `.git`），并新增 `repos/SOURCES.md`。
  - 参考资料和上游仓库的重媒体默认 git 忽略；需要版本化用 Git LFS。
- **原因**：
  - AIWork 是长期工作空间，需要输入（Skill/源码/素材）与输出（成品）彻底分离。
  - 避免每个作品复制一份引擎，改为共享引擎 + `CINE_ROOT`。
  - 让 opencode 从仓库内读取 Skill，减少对用户目录的隐式依赖。
- **影响**：
  - 旧路径 `~/vibe-knowledge`、`~/Desktop/vibe-knowledge`、`~/.claude/skills` 不再使用。
  - 新作品必须通过 `projects/<slug>/` + `CINE_ROOT` 渲染。
  - 旧作品已迁移到 `projects/benford`、`projects/sangetsuki`，成品在 `out/`。
- **迁移**：
  - 旧 `examples/vk/lessons/*` → `projects/<work>/lessons/*`。
  - 旧 `交付/*` → `out/<work>/<日期>_<版本>/`。
  - 旧 `风格图鉴` → `resources/styles/vibe-knowledge-gallery/`。
  - 旧 `山月记-素材` → `resources/images/sangetsuki/`。
  - 旧 `山月记-效果图` → `projects/sangetsuki/design/`。
- **相关 commit / files**：
  - `2edc89b` 重构 AIWork 为作品优先工作空间
  - `AGENTS.md`、`opencode.json`、`workspaces/vibe-knowledge/tools/new_project.py`
  - `workspaces/vibe-knowledge/cine/tools/{record.py,finish.py,clips.py}`
