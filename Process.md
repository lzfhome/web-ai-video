# Process

记录 AIWork 的**代码架构变化**。只记架构，不记内容。

## 什么算架构变化

- 目录结构、模块边界、文件放置规则
- 引擎 / 渲染管线 / 路径契约（`CINE_ROOT`、`/cine/*` 映射、`projects` 布局）
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

## 2026-11-19 · 新增视频右上角水印工具

- **变更**：
  - 新增 `cine/video/engines/watermark.py`：对单个视频或目录批量叠加右上角文字水印；默认 dry-run，`--yes` 执行；默认输出 `<原名>_wm.mp4`，`--inplace` 先备份 `.bak` 再替换。
  - 默认字体 `C:/Windows/Fonts/msyh.ttc`，字号 `h*0.028`，边距 `w/h*0.03`，白色 35%，黑色阴影。
- **原因**：成片需要在每一场景右上角带作者水印，且不修改 `poem.json` / `poetry.js`，现有和以后的项目都能复用。
- **影响**：只影响显式调用该工具的视频；渲染管线不变。
- **迁移**：无；对已有 `build/lesson*.mp4` 或 `deliveries/**/video.mp4` 手动跑一次即可。
- **相关 files**：`cine/video/engines/watermark.py`、`cine/video/AGENTS.md`

---

## 2026-11-17 · poetry 单卡/多卡按场景切换

- **变更**：
  - `compose.py`：`scene.cards` 只有 1 张时展平为旧 `lines` 场景，走逐字/逐行 + 署名延迟；2 张及以上才保留 `cards`，走整块淡入淡出。同一支片可按场景混用。
  - 多卡 `poem.json` 不再重复写顶层 `lines / type / credit / source / quotes / narration / pacing / footer2`，这些只保留在每张卡里。
  - `retime.py` 复用 `compose.card_hold()`；`poetry.js` 抽出共用的 `layoutText()`，删除未使用的 `SCENE`；`render.py` 的校验和 `beats` 支持 `cards`。
  - `schema.json` 允许 `cards` 最少 1 张。
- **原因**：单卡场景应保持旧版文字特效，多卡场景才用整块切换；模式按场景决定，不按整支片子决定。
- **影响**：单卡 `work.json` 仍写 `cards`，合成后自动变成旧场景；2 张以上多卡的时长和视觉不变。旧作品不需要改。
- **迁移**：重跑 `compose.py` 或 `project.py build poetry --work ...` 即可；已交付成片不受影响。
- **相关 files**：`workspaces/vibe-knowledge/line/poetry/{compose.py,retime.py,render.py,poetry.js,schema.json,TEMPLATE.md,AGENTS.md,SOURCES.md}`

---

## 2026-11-14 · poetry 章节行补全（对齐诛仙版式）

- **变更**：
  - `source` 字段改为“第X章 章名”；`footer` 继续写“《书名》· 第X册”。
  - 章节行仍按诛仙版式：署名下方一行，跟在台词之后出现，`source_size` 18。
- **原因**：之前 `source` 只写“第X册 卷名”，卡片上看不到章数；用户要求与诛仙版式一致。
- **影响**：`poem.json` 的 `source` 语义变化：从“册名”改为“章名”；旧作品需把 `source` 改成章名，或在 `footer` 保留册名。
- **迁移**：重渲；旧作品若 `source` 仍是册名，卡片会显示“第X册”而不是章名。
- **相关 files**：`line/poetry/{poetry.js,defaults.json,TEMPLATE.md}`、`tools/local/qijie/work/*`

---

## 2026-11-13 · poetry 模板化：引擎归 line，作品只留数据

- **变更**：
  - poetry 引擎从 `cine/video/engines/dom/poetry.js` 迁到 `line/poetry/poetry.js`；`cine` 只保留 core/util/record/audio/deliver 等公共能力。
  - 新增 `line/poetry/film.js`：入口从 `project.json` 的 lesson 读 `poem.json`，引擎不再拷进作品。
  - `core.js` 优先按 `project.json` 的 `workspace + line` 加载 `/line/<workspace>/<line>/film.js`，失败回退旧 `/lessons/<id>/film.js`。
  - `tools/lib/server.py` 新增 `/line/<workspace>/<line>/...` 路由。
  - `project.py build poetry` 不再往作品复制 `film.js`；新增 `--work <work.json>`，走 `compose.py` 合成。
  - 新增 `line/poetry/{defaults.json,compose.py,schema.json,build.skeleton.json,TEMPLATE.md,examples/zhuxian.work.json}`：work（题材/N 场/封面/BGM/内容）→ poem。
  - `poetry-tts` 骨架改为引用 `/line/vibe-knowledge/poetry/poetry.js`。
  - `project.py` 自动探测 `tools/local/ffmpeg/*/bin` 并写入 `FFMPEG`/`PATH`，换 Agent 不用手工设环境。
  - `line/poetry/render.py` 增加 BGM 长度检查：短于成片时提前警告。
  - `AGENTS.md` 新增「Agent 可执行标准（强制）」：AGENTS/TEMPLATE、根目录命令、样例与 smoke test、文档与代码一致。
- **原因**：把“cine 公共能力 / line 私有机制 / work 内容”分层；以后新题材只写 work，不改引擎和作品代码。
- **影响**：poetry 作品目录只剩 `poem.json` + `assets` + `build`，无 JS；老项目仍可走旧 `film.js` 与 cine 里的 legacy poetry.js。
- **迁移**：新作品用 `python project.py build poetry --work <work.json> --name <slug>`；旧作品不动。
- **相关 files**：`cine/video/engines/dom/{core.js,poetry.js}`、`tools/lib/server.py`、`project.py`、`workspaces/vibe-knowledge/line/poetry/*`、`line/poetry-tts/film.skeleton.js`

---

## 2026-11-12 · image 拆分 + 共享 ffprobe 探测

- **变更**：
  - 新增 `cine/image/lib/ark_client.py`：配置、HTTP、图片生成、视频任务轮询、下载。
  - `cine/image/engines/ark.py` 只留 CLI：dry-run 计划、落盘、批量 `assets`、拆帧。
  - `tools/lib/ffmpeg.py` 新增 `ffprobe()` / `probe_duration()` / `probe_fps()`；优先 `FFPROBE`，其次 ffmpeg 同目录，最后 PATH。
  - `cine/audio/engines/tts_doubao.py`、`tts_edge.py`、`line/dom-narrated/finish.py`、`line/poetry-tts/render.py` 删除各自的探测实现，改用共享函数。
- **原因**：
  - 同一段 ffprobe 解析在四个文件里重复；image 的 HTTP 逻辑和 CLI 混在一起。
- **影响**：
  - 行为不变；`FFPROBE` 环境变量仍然优先。
- **验证**：
  - `python tools/smoke_test.py` 通过。
  - `python cine/image/engines/ark.py image|video` dry-run 正常。
- **相关文件**：
  - `cine/image/{lib,engines}/**`、`tools/lib/ffmpeg.py`、`cine/audio/engines/tts_*.py`、`line/dom-narrated/finish.py`、`line/poetry-tts/render.py`

---

## 2026-11-12 · cine/video 与 cine/image 分层对齐

- **变更**：
  - `cine/video/dom` → `cine/video/engines/dom`；`cine/video/canvas` → `cine/video/engines/canvas`。
  - `cine/video/deliver.py`、`queue.py` → `engines/`；`update_series.py` → `tools/`。
  - `cine/image/ark.py` → `cine/image/engines/ark.py`。
  - 同步：`tools/lib/server.py` 的 `/cine/*` 映射、`record.py` / `stills.py` / `clips.py` / `retail.py` 的 `parents`、`doctor.py`、`smoke_test.py`、`project.py`、`line/*/render.py`、各 AGENTS.md。
  - `dom/index.html` 的入口改成绝对路径 `/cine/video/engines/dom/core.js`（相对路径在 `/cine/index.html` 下会解析错）。
- **原因**：
  - 与 `cine/audio` 的「零件 / 引擎 / 客户端 / 工具」分层保持一致。
- **影响**：
  - URL 契约不变：`/cine/index.html`、`/cine/engine/*`、`/cine/canvas/*` 仍可用。
  - 旧文件路径 `cine/video/dom/*`、`cine/video/deliver.py` 等不再存在。
- **验证**：
  - `python tools/smoke_test.py` 通过（DOM 录制 + 混音 + 交付）。
  - `python project.py render sky-blue --line canvas-bgm` 通过（13.7s）。
  - `python cine/image/engines/ark.py image ...` dry-run 正常。
- **相关文件**：
  - `cine/video/**`、`cine/image/**`、`tools/lib/server.py`、`tools/doctor.py`、`tools/smoke_test.py`、`project.py`

---

## 2026-11-12 · cine/audio 分层重构（零件 / 引擎 / 客户端 / 工具）

- **变更**：
  - `cine/audio` 拆成四层：`lib/`（零件）、`engines/`（引擎）、`clients/`（被 import 的客户端）、`tools/`（取素材/检查的工具）。
  - 引擎迁移：`tools/{bed,score,loopbed,silent_timings,edge_tts_timings,tts_doubao_timings}.py` → `engines/{bed,score,bgm_loop,tts_silent,tts_edge,tts_doubao}.py`。
  - `doubao_tts.py` → `clients/doubao_tts.py`；更新 `engines/tts_doubao.py`、`line/poetry-tts/render.py`、`tools/video-studio/tts_client.py` 的引用。
  - 新增 `lib/wavio.py`（`SR` / `read_wav` / `write_wav` / `fit_to`）、`lib/dsp.py`（`envelope` / `duck_gain` / `limiter`）、`engines/mix.py`（`combine` / `finalize`）。
  - `line/dom-narrated/finish.py` 删除本地的 WAV/DSP 实现，改用 `lib` + `engines/mix.py`。
  - 迁移期间的兼容壳已删除；`tools/` 下只保留 `get_bgm.py`、`musicdl_bgm.py`、`check_timings.py`。
- **原因**：
  - 引擎和工具混在 `tools/`，混音逻辑散在产线里，无法复用。
  - 明确“零件 → 引擎 → 产线”三层，后续环境声等新引擎有固定落点。
- **影响**：
  - 旧路径 `cine/audio/tools/bed.py` 等不再存在；line 脚本、doctor、smoke 已同步。
  - `tools/smoke_test.py` 通过（3 秒端到端）。
- **相关文件**：
  - `cine/audio/{lib,engines,clients,tools}/**`
  - `workspaces/vibe-knowledge/line/{dom-narrated,poetry,poetry-tts}/**`
  - `tools/smoke_test.py`、`tools/video-studio/tts_client.py`、`AGENTS.md`

---

## 2026-11-11 · 新增 poetry-tts 产线（书封诗句 + 豆包配音）

- **变更**：
  - 新产线 `line/poetry-tts/`：`build.json`、`film.skeleton.js`、`render.py`、`AGENTS.md`。
  - `render.py` 先逐场合成配音、测时长，再回写 `poem.json` 的 `seconds` 与 `gap`（`image_in` / `text1` / `credit` / `line_step`），然后拼 `build/narration.wav` + `build/timings.json`，最后交给 `dom-narrated` 渲染（timings 已存在，不会重算）。
  - `cine/video/dom/poetry.js` 支持 `gap.line_step`（多行走场间隔），默认 0.28。
  - `project.py` 的 `--line` 增加 `poetry-tts`；入口仍是 `python project.py build poetry-tts`。
  - 配音缓存写在 `build/audio/scXX.json`，文案/音色/语速不变就不重复合成。
- **原因**：
  - 需要「书封 + 诗句 + 真配音」的产线，且每场时长要跟着配音走，而不是固定 10 秒。
- **影响**：
  - `poetry` 保持不变（BGM-only）；`poetry-tts` 依赖豆包语音 key。
  - 场数、配色、版式、封面、BGM 的写法与 `poetry` 完全一致。
- **相关文件**：
  - `workspaces/vibe-knowledge/line/poetry-tts/**`
  - `cine/video/dom/poetry.js`、`project.py`、`AGENTS.md`

---

## 2026-11-11 · 接入豆包语音合成（Seed-TTS 2.0）

- **变更**：
  - 新增 `cine/audio/doubao_tts.py`：豆包语音客户端（`synth()` + 命令行），走 `openspeech.bytedance.com/api/v3/tts/unidirectional`，鉴权 `X-Api-Key` + `X-Api-Resource-Id`。
  - key 查找顺序：参数 → `DOUBAO_TTS_API_KEY` / `TTS_API_KEY` → `~/.config/aiwork/tts.env` → `tools/video-studio/config.secrets.json` 的 `tts_api_key`。
  - 新增 `cine/audio/tools/tts_doubao_timings.py`：`narration.json` → `timings.json` / `narration.wav`，沿用 edge-tts 的字符权重对齐。
  - `line/dom-narrated/render.py` 和根 `project.py` 的 `--tts` 增加 `doubao`；`narration.json` 可写 `voice.engine: doubao`。
  - `tools/video-studio` 新增「配音」页：`tts_client.py` 复用 `cine/audio` 的实现，新增 `/api/tts`、`/api/tts/voices`、`/api/tts/files`、`/api/tts/{filename}`，产物落 `data/gen_audio/`。
  - `config.py` 的 `SECRET_KEYS` / `DEFAULT_CONFIG` 增加 `tts_api_key`。
- **原因**：
  - 方舟 API Key（`ark-`）和豆包语音 Key（UUID）不通用，必须单独接一条线路。
  - 配音既要在工作台里试听，也要能在产线里自动出时间轴，两处共用一份实现避免参数漂移。
- **影响**：
  - `poetry` 仍是 BGM-only（`sync_poem` 固定写 `mode: silent`），要旁白需另改。
  - edge-tts 保留，`--tts edge` 行为不变。
- **迁移**：
  - 无破坏性；旧项目不加 `voice.engine` 仍走 silent。
  - 新项目配音：`--tts doubao`，或 `narration.json` 写 `{"engine":"doubao","voice":"…","speed":0.92}`。
- **相关文件**：
  - `cine/audio/doubao_tts.py`、`cine/audio/tools/tts_doubao_timings.py`
  - `workspaces/vibe-knowledge/line/dom-narrated/render.py`、`project.py`
  - `tools/video-studio/{app.py,config.py,tts_client.py,static/*}`

---

## 2026-11-11 · 移除 poetry 的水痕特效与 WebGL 层

- **变更**：
  - 删除 `cine/video/dom/poetry-gl.js`。
  - `cine/video/dom/poetry.js` 回到纯 DOM/CSS：背景、书封、雾、光斑、浮尘、颗粒、暗角。
  - `cine/video/dom/core.js` 恢复无条件 `post.finish`，移除 `NO_POST` / `window.__NO_POST` 分支。
  - `line/poetry/build.json` 移除 `drops*` 全部参数；`FX` 同步删除。
- **原因**：水珠/水痕效果未达预期，用户决定去掉背景水滴特效。
- **影响**：poetry 不再依赖 WebGL，渲染更快、码率更低；画面与「双场景 30 秒」版本一致，只是没有雨。
- **相关文件**：`cine/video/dom/{poetry.js,core.js}`、`line/poetry/{build.json,AGENTS.md}`

---

## 2026-11-11 · poetry 改用 WebGL 渲染水珠

- **变更**：
  - 新增 `cine/video/dom/poetry-gl.js`：背景与书封在 2D canvas 里烘焙成纹理，片元着色器按网格生成水珠并做真实折射；暗角、颗粒、光晕也在着色器里。
  - `cine/video/dom/poetry.js` 改为调用 `PoetryGL`；诗句、角标、雾、光斑、浮尘仍在 DOM 层。
  - `cine/video/dom/core.js` 支持跳过后期：`film.NO_POST` 或 `window.__NO_POST` 为真时不再执行 `post.finish`，由镜头直接画到画布。
  - poetry 参数去掉 `drops_blur`，新增 `drops_spec`。
- **原因**：纯 CSS 水珠只能做渐变贴图，无法真实扭曲背后的画面。
- **影响**：poetry 的渲染依赖 WebGL；文字仍在 DOM，所以排版和字体不受影响。旧作品（没有 NO_POST 导出）由 `window.__NO_POST` 兼容。
- **相关文件**：`cine/video/dom/{poetry.js,poetry-gl.js,core.js}`、`line/poetry/{build.json,AGENTS.md}`

---

## 2026-11-11 · 删除 4 条产线

- **变更**：
  - 删除 `line/{canvas-ai,dom-ai,rpg-qa,hybrid-ai}`（render.py / 骨架 / 文档一并删除）。
  - `project.py render --line` 只剩 `canvas-bgm` / `dom-narrated` / `poetry`；移除 `--generate-assets` 及对应分支。
  - `project.py list` 对 `line` 已不存在的旧作品标注「产线已删」。
  - `cine/image/ark.py`、`cine/video/dom/rpg-qa.js` 保留：它们是引擎/工具，不再有产线默认调用。
- **原因**：实际只用 poetry；其余产线不再维护，减少索引和文档噪音。
- **影响**：`moon-follow`、`moon-follow-rpg`、`qa-ai-pixel-demo` 不能再重渲，旧成片保留。
- **相关文件**：`project.py`、`AGENTS.md`、`cine/image/AGENTS.md`、`cine/video/canvas/AGENTS.md`、`cine/video/dom/AGENTS.md`

---

## 2026-11-11 · poetry 产线参数化（poem.json 契约）

- **变更**：
  - 新增 `cine/video/dom/poetry.js`：poetry 的渲染引擎，只负责「怎么画」；版式、调色板、特效、时长全部来自参数。
  - `line/poetry/film.skeleton.js` 缩成 6 行：fetch `./poem.json` → `createPoetryFilm(poem, import.meta.url)` → 再导出。
  - `line/poetry/build.json` 同时充当参数模板：字段和默认值就是文档，不再维护第二份 skeleton。
  - `line/poetry/render.py` 先从 `poem.json` 生成 `narration.json` 与 `timings.json`（静音时间轴），场景时长与成片时长只有一个来源；`--keep-narration` 可跳过。
  - 新增 `line/poetry/build.json`：poetry 的唯一输入文件（id / 素材路径 / 全部版式参数），支持 `//` 注释（按 JSONC 解析）；`python project.py build poetry` 读它建一个新项目（自动命名、复制素材、生成 `poem.json`），再渲染交付。
  - 调色板收进引擎：`jade / ember / moon / ink`；场景可用任意 palette 键覆盖（`text` / `halo` / `rain` 等）。
  - 文档改为「跟着目录走」：每条 `line/<name>/AGENTS.md` 写用途 / 改哪个文件 / 参数 / 渲染命令；每个 `cine/` 子目录的 AGENTS.md 写职责 / 文件清单 / 调用方。根 `AGENTS.md` 只保留规则和索引。
  - 不新增建项目的 CLI：新建作品仍是复制 line 骨架，人和 agent 的接口是目录 AGENTS.md + 内容文件。
  - `projects/zhuxian-poem` 迁移为 `poem.json` 实例，`film.js` 改为通用 wrapper。
- **原因**：换一首诗不该改代码；line 要像函数一样「传参即用」，新会话只看 AGENTS.md + poem.json 就能出片。
- **影响**：
  - poetry 的出片入口：改 `line/poetry/build.json` → `python project.py build poetry`；每次生成一个新项目文件夹，旧片不动。
  - 项目里的 `poem.json` 是快照，`narration.json` 由它派生，都不要手改。
  - 渲染入口不变：`python project.py render <name> --workers 2`。
  - 旧写法（在 film.js 里写死版式）仍可运行，但不再作为模板。
- **迁移**：`zhuxian-poem` 已迁移并重新出帧验证（画面一致）。
- **相关文件**：
  - `cine/video/dom/poetry.js`
  - `workspaces/vibe-knowledge/line/poetry/{build.json,film.skeleton.js,render.py,AGENTS.md}`
  - `line/<各产线>/AGENTS.md`、`cine/<各子目录>/AGENTS.md`

---

## 2026-11-10 · 车间 / 产线 / 引擎 / 产物四层迁移

- **变更**：
  - 目录模型改为：`resources/`（原料）→ `cine/`（共享引擎）→ `workspaces/vibe-knowledge/line/`（产线）→ `workspaces/vibe-knowledge/projects/`（产物）。
  - `cine/` 置顶：`audio/`、`video/{dom,canvas}/`、`image/`、`vendor/`。删除 `workspaces/vibe-knowledge/cine/`。
  - 共享基础设施从 `cine/lib/` 移到 `tools/lib/`：`paths.py`、`ffmpeg.py`、`browser.py`、`server.py`、`scaffold.py`、`console` 行为内联。
  - 原 `cine/pipelines/{canvas,deliver,queue}.py` 拆到 `line/canvas-bgm/render.py`、`cine/video/deliver.py`、`cine/video/queue.py`。
  - 原 `cine/tools/{record,stills,clips,retail}.py` 移到 `cine/video/dom/`；`finish.py` 移到 `line/dom-narrated/finish.py`；`loopbed.py` 移到 `cine/audio/tools/`。
  - 新增 `line/{canvas-bgm,canvas-ai,dom-narrated,dom-ai,rpg-qa,poetry,hybrid-ai}/render.py`；`project.json` 记录 `line`，根目录 `project.py render` 按产线分发。
  - `canvas-ai` = `cine/image` 生成素材 + `cine/video/canvas` 快速合成；骨架 `line/canvas-ai/film.canvas.skeleton.js`，默认不生成素材（要 `--generate-assets`）。
  - `dom-ai` = `cine/image` 生成素材 + `cine/video/dom` + `cine/audio`；骨架 `line/dom-ai/film.skeleton.js`，默认调用 `line/dom-narrated/render.py`。
  - `rpg-qa` = 像素场景 + RPG 对话框 + 问答选项 + AI 双人形象；引擎 `cine/video/dom/rpg-qa.js`，骨架 `line/rpg-qa/film.skeleton.js`，渲染复用 `line/dom-narrated/render.py`。
  - `poetry` = 书封放大虚化做背景 + 代码诗句卡片 + 自定义 BGM；骨架 `line/poetry/film.skeleton.js`，渲染复用 `line/dom-narrated/render.py`。
  - 删除 `workspaces/vibe-knowledge/templates/`；`line` 就是模板：新建项目直接复制 `line/canvas-bgm/film.canvas.skeleton.js`、`line/dom-narrated/film.skeleton.js`。`tools/lib/scaffold.py` 只作为 smoke test 内部脚手架。
  - `resources/` 接管原料：`cine/fonts`、`cine/audio/sfx`、`skills/vibe-knowledge/assets/{music,voice}`、`skills/vibe-knowledge/styles` 全部迁入。
  - 删除 `workspaces/vibe-knowledge/tools/`：不再有 `new_project` 命令；timings 移到 `cine/audio/tools/`；`update_series.py` 移到 `cine/video/`；`migrate_layout.py` 删除；`session/` 移到 `tools/session/`。
  - 删除根 `projects/` 和 `out/`：作品移到 `workspaces/vibe-knowledge/projects/`，旧 `out/<work>/*` 移到各项目 `deliveries/`。
  - 静态服务器改为映射共享引擎：`/cine/index.html` → `cine/video/dom/index.html`；`/cine/{engine,canvas,fonts,audio/sfx}` 做旧路径别名；`/resources/*` → `resources/`。
  - 删除 `tools/vk.py`；根目录新增 `project.py`：扫描所有 `workspaces/*/projects/*`，提供 `list / show / lines / render / deliver / qa`。不再有 `vk new`。
- **原因**：
  - 旧结构把原料、引擎、流水线、作品源码、成品混在一起；`cine/tools` 持续堆积业务脚本。
  - 需要「同一车间多产线、同一引擎多车间复用」的清晰边界。
- **影响**：
  - `projects/` 整个目录不再进 git（源码 + build + deliveries）。
  - 项目里不再有 `cine`、`build`、`stills` 链接；`CINE_ROOT` 指向项目根即可。
  - 旧项目 `film.js` / `film.canvas.js` 里的 `../../cine/engine|canvas/*` 由服务器别名兼容，不需要改作品源码。
  - 旧 `out/` 路径、`workspaces/vibe-knowledge/tools/*`、`workspaces/vibe-knowledge/cine/*` 不再存在。
- **迁移**：
  - 已测：`project.py list / show / lines / render / deliver / qa`、`project.py render sky-blue`（30s/30fps 7.8s）、DOM `record.py` 1s、`finish.py --audio-only`、`tools/smoke_test.py`。
- **相关文件**：
  - `cine/**`、`tools/lib/**`、`project.py`
  - `workspaces/vibe-knowledge/line/**`
  - `AGENTS.md`、`.gitignore`

---

## 2026-11-10 · 代码分层重构

- **变更**：
  - 新建 `workspaces/vibe-knowledge/cine/lib/`：`paths.py`、`ffmpeg.py`、`browser.py`、`server.py`、`console.py`，统一共享基础设施。
  - 新建 `workspaces/vibe-knowledge/cine/pipelines/`：`canvas.py`、`deliver.py`、`queue.py`，从 `cine/tools/` 移入。
  - `cine/tools/{server,browser,encoders,render_canvas,deliver,queue}.py` 保留为兼容 wrapper，旧命令不破坏。
  - 新增 `workspaces/vibe-knowledge/ARCHITECTURE.md`：定义「加功能放哪一层」，明确不要往 `cine/tools` 堆业务脚本。
  - 新增统一 CLI `tools/vk.py`：`doctor / smoke / new / render / deliver / qa / prune / list`；`render` 根据 `film.canvas.js` 自动选择 Canvas 或 DOM 管线。
  - `record.py` / `finish.py` / `stills.py` / `clips.py` 改为直接 import `cine.lib.*`，不再依赖本目录 wrapper。
- **原因**：
  - 功能增多后，`cine/tools` 同时承担引擎工具、流水线、基础设施，新增功能没有固定落点。
  - 统一入口减少「记很多脚本路径」的负担。
- **影响**：
  - 旧命令（`cine/tools/render_canvas.py` 等）仍可用；新命令优先 `python tools/vk.py`。
  - 新功能规则：基础设施进 `cine/lib`，组件进 `cine/engine` 或 `cine/canvas`，流程进 `cine/pipelines`，CLI 进 `tools/vk.py`。
  - 项目/素材仍在 `projects/`，输出仍在 `out/`。
- **迁移**：
  - 已测试：`vk list`、`vk render sky-blue --mode canvas`、`vk qa sky-blue`、`vk deliver`，30s 渲染 7.65s。
- **相关文件**：
  - `workspaces/vibe-knowledge/{ARCHITECTURE.md,cine/lib/*,cine/pipelines/*}`
  - `workspaces/vibe-knowledge/cine/tools/*`（wrapper / 引擎工具）
  - `tools/vk.py`、`AGENTS.md`、`workspaces/vibe-knowledge/AGENTS.md`

---

## 2026-11-10 · Canvas 快速通道（BGM-only）

- **变更**：
  - 新增 `workspaces/vibe-knowledge/cine/canvas/`：`engine.js`（Canvas → WebCodecs → Mediabunny → MP4）、`components.js`（`title / keyword / counter / bars / plate / foot / chapter / progress / spectrum / waves / sunset`）。
  - 新增 `cine/tools/render_canvas.py`：加载 `lessons/<lesson>/film.canvas.js`，启动静态服务器，浏览器内逐帧编码，写 `build/lesson<lesson>.mp4`，再 mux 默认 BGM。
  - `film.canvas.js` 契约：导出 `duration / fps / images / build(c)`；`build` 返回 `{from, to, draw(t, c)}` 镜头数组，`draw` 按绝对时间 `t` 画一帧。
  - `canvas/vendor/mediabunny.js` 是 Mediabunny 0.x 的 ESM bundle（MPL-2.0，见同目录 AGENTS.md）。
  - 新增示例作品 `projects/sky-blue`（30s BGM-only，「天空为什么是蓝的」）。
- **原因**：
  - 当前 `record.py` 每帧 `page.screenshot()` 37ms，瓶颈在截图/JPEG/回读；Canvas 直接编码可以完全绕开。
  - BGM-only 知识片不需要旁白/时间轴，适合 Canvas 数据驱动渲染。
- **实测**：
  - 30s/30fps/900 帧：渲染+编码 7.20s，BGM 0.66s，总计 7.86s。
  - 30s/60fps/1800 帧：渲染+编码 11.46s，BGM 0.72s，总计 12.18s。
  - 对比当前 DOM 引擎 30s/30fps 的 21s。
- **影响**：
  - Canvas 路径只支持 Canvas/WebGL 能画的视觉；现有 DOM/CSS 组件（`know.js`）仍走旧 `record.py`。
  - `render_canvas.py` 不需要 `record.py`/`finish.py`，也不依赖 4 个 Chrome 进程；一个浏览器页面即可。
  - 画质：H.264 20Mbps 输入，BGM AAC 192k；文字边缘无 JPEG 压缩。
- **相关文件**：
  - `workspaces/vibe-knowledge/cine/canvas/{index.html,engine.js,components.js,vendor/}`
  - `workspaces/vibe-knowledge/cine/tools/render_canvas.py`
  - `projects/sky-blue/lessons/sky-blue/film.canvas.js`
  - `out/sky-blue/2026-11-10_canvas-fast-{30fps,60fps}/`

---

## 2026-11-10 · Windows 可运行闭环

- **变更**：
  - 新增 `requirements.txt`、`tools/doctor.py`：统一检查 Python / ffmpeg / numpy-scipy-pillow-playwright / 字体 / BGM / 密钥。
  - 新增 `tools/smoke_test.py`：3 秒无声 lesson 端到端跑 `new_project → silent_timings → record → finish → deliver`，成功后清理。
  - 新增 `tools/prune_tmp.py`：默认 dry-run 清理 `out/_tmp` 的可再生中间产物；保留旁白/timings/lesson.json/成片，每个作品默认保留最新 1 个 `picture.mp4`，删除旧 picture、混音缓存、封面中间片、qa/esfx。
  - 新增 `workspaces/vibe-knowledge/cine/tools/server.py`：`record.py` / `stills.py` / `finish.py` / `clips.py` 自动起本地静态服务器，并把 `/cine/*` 映射到共享引擎；项目里不再依赖 `cine` 目录才能渲染。
  - `record.py` / `clips.py` / `finish.py` 的 `CINE_ROOT` 统一 `.resolve()`；`finish.py` 的 `CINE` 改为脚本所在引擎目录，不再假设项目里有 `cine/`。
  - 新增 `queue.py` / `deliver.py`：Python 版渲染队列和交付，替代 zsh 专用的 `queue.sh` / `deliver.sh`；`queue.py` 带 lock，避免并发写坏 `picture.mp4`。
  - 新增 `migrate_layout.py`：把旧项目的 `cine` / `build` / `stills` 目录副本迁移成 junction/symlink，并把 `out/_tmp/<work>/<kind>-<lesson>` 改名为 `out/_tmp/<work>/<lesson>/<kind>`；默认 dry-run。
  - `new_project.py`：目录链接优先 symlink，Windows 回退 `mklink /J`，再回退复制；替换 `__ID__ / __TITLE__ / __TPL__`；新增 `--narration A–F`；创建 `assets/{img,clips,audio}`；`project.json` 记录 `narration / fps / resolution`。
  - 去掉硬编码绝对路径：`finish.py` 的 `VK_TOOLS` 改为向上查找 + `VK_TOOLS` 环境变量；`ark_media.py` 的 `VIDEO_STUDIO_DIR` 默认从 `__file__` 推导；`video-studio/app.py` 的 `MOVE_BASE` 改为 `VIDEO_STUDIO_MOVE_BASE` 或仓库相对路径。
  - `qa.py`：OCR 改为可选（无 `swiftc` 时跳过）；字体跨平台 fallback；短视频 BGM 相关性检查不再因片长 < 8 秒直接判 0。
  - `bgm_force.py`：`prepare(..., root=)` 会检查 `bgm.wav` 是否真实存在，缺失时自动生成 `bgm_auto.wav`，不再让 `finish.py` 因模板里的占位 BGM 报错。
  - 画质链：`record.py` 默认 JPEG q95 + CRF16（`--shot png` 可选，画质更好但慢约 5 倍）；`finish.py` 在无 `clips` / `COLD_SRC` 且 fps 一致时直接 copy 视频流，否则用 `--crf`（默认 18）重编码；`deliver.py` 默认 copy，只有 `--reencode` / `--web` 才二次压缩。
  - 渲染并行：`record.py --workers N` 把时间轴切成 N 段，每段独立浏览器 + x264，最后 `concat -c copy`；上限 4（6/8 路会因浏览器实例过多卡在页面加载）。实测 5s/30fps：单进程 12.2s，4 路 7.6s，SSIM 0.9956、PSNR 50.9dB；30s/30fps/900 帧 4 路 38s，帧数完整。
  - 新增 `encoders.py`：`--encoder nvenc` 会先跑 1 帧测试；驱动/ffmpeg 不匹配时自动回退 x264，不阻塞渲染。
  - `stills.py` / `qa.py` 字体加入 Windows 路径；各入口加 `sys.stdout.reconfigure(errors="replace")`，避免 GBK 控制台因 `✓ / → / ⚠` 崩溃。
  - `video-studio/run.sh` 默认只绑 `127.0.0.1`，可用 `VIDEO_STUDIO_HOST` 覆盖；`_upload_path` 加路径穿越校验。
- **原因**：
  - 当前仓库在 Windows 上运行，旧管线依赖 zsh、软链、`/home/oliver` 绝对路径和 macOS `swiftc`。
  - `out/` 契约要求中间产物只落在 `out/_tmp/`，但 Windows 上用目录复制绕过了软链，导致 `projects/` 和 `out/_tmp/` 各存一份。
- **影响**：
  - 渲染不再需要手动起 `python -m http.server`，也不要求项目里存在 `cine/` 目录。
  - Windows 上 `new_project.py` 可直接建项目；`queue.py` / `deliver.py` 可批量出片。
  - 旧的 `queue.sh` / `deliver.sh` 保留但仅作 macOS/Linux 兼容入口；新流程优先用 Python 版。
  - 已执行迁移：`projects/*/cine` 和 `build` / `stills` 现在是 junction（Windows）或 symlink（POSIX），不再入库；`out/_tmp` 成为唯一中间产物目录。
  - `projects/*/cine` / `build` / `stills` 的旧 tracked symlink 已从 Git 索引移除，避免 Windows `core.symlinks=false` 下反复出现 deleted。
- **迁移**：
  - 装 Python 3.12 + ffmpeg，然后 `python -m pip install -r requirements.txt`、`python -m playwright install chromium`、`python tools/doctor.py`。
  - 新项目直接用 `new_project.py`；旧项目/新克隆跑
    `python workspaces/vibe-knowledge/tools/migrate_layout.py --yes` 恢复本地链接（默认 dry-run）。
- **相关 commit / files**：
  - `requirements.txt`、`tools/doctor.py`
  - `workspaces/vibe-knowledge/cine/tools/{server.py,queue.py,deliver.py,record.py,clips.py,finish.py,stills.py}`
  - `workspaces/vibe-knowledge/tools/{new_project.py,check_timings.py,update_series.py,silent_timings.py}`
  - `skills/vibe-knowledge/tools/{qa.py,bgm_force.py,ark_media.py,fit_bgm.py}`
  - `tools/video-studio/{app.py,run.sh}`、`AGENTS.md`、`workspaces/vibe-knowledge/AGENTS.md`

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
