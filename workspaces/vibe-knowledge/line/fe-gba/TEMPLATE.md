# fe-gba 模板（Agent 操作手册）

这条产线只做一件事：**GBA 火焰纹章的单镜头测试片**。  
输入是 `work.json`，输出是 `build/<shot>.mp4` 和接触表。不是整片，也不是图集。

## 输入变量

| 变量 | 说明 |
|---|---|
| `title` | 这条测试的标题 |
| `source` | 作品名 + 角色 + 原画来源 URL |
| `story` | 一句话剧情，必须能说清“这场发生什么” |
| `style` | 全片统一风格（GBA 火纹官方插画、赛璐璐、色调） |
| `style_lock` | 角色锁定：脸、发色、服装、武器、禁止改动项 |
| `characters` | 角色名、作品、原画文件 |
| `shots[]` | 镜头列表；当前一条镜头一个 5–30 秒片段 |

## 目录契约

```text
projects/<work>/lessons/<lesson>/
├── work.json
├── assets/
│   ├── eirika-serenes.jpg       # 原画参考
│   └── ...
└── build/
    ├── S01_keyframe.png         # 先出帧图
    ├── S01.mp4                  # 再出视频
    └── S01_contact.jpg          # QA 接触表
```

`work.json` 里的路径**相对于 lesson 目录**，不要写 `D:\` 绝对路径。

## 最小结构

```json
{
  "title": "圣魔之光石 · Eirika · 5s 测试",
  "source": "Fire Emblem: The Sacred Stones / Serenes Forest",
  "story": "Renais 被 Grado 入侵后，Eirika 在城堡庭院迎战逼近的敌军。",
  "style": "GBA 火焰纹章官方插画风格，赛璐璐上色，清晰轮廓，复古奇幻色调",
  "style_lock": "绿色长发、红色上衣、金色胸甲、白色短裙、蓝色裙边、红色长靴、金色护肩、细剑；不要改成纯白连衣裙",
  "characters": {
    "Eirika": "assets/eirika-serenes.jpg"
  },
  "shots": [
    {
      "id": "S01",
      "title": "Eirika · Renais 庭院",
      "story": "Eirika 在庭院中面对逼近的 Grado 军队。",
      "reference_images": ["assets/eirika-serenes.jpg"],
      "keyframe": "build/S01_keyframe.png",
      "keyframe_prompt": "16:9 横构图，GBA 火焰纹章官方插画风格：Eirika 站在 Renais 城堡石砌庭院中央，绿色长发、红色上衣、金色胸甲、白色短裙、蓝色裙边、红色长靴、金色护肩，细剑已出鞘，剑尖斜指地面；背景远处 Grado 士兵和旗帜，夕阳与尘土；全身构图，无文字，无 UI，无 watermark。",
      "video_prompt": "从首帧开始，Eirika 将细剑缓缓抬至胸前，剑尖斜指前方，随后抬眼看向镜头；披风与头发随风摆动，地面尘土飞扬；镜头缓慢推近；远处 Grado 士兵保持队形，旗帜飘动；保持红色上衣、金色胸甲、白裙蓝边、红靴、金护肩、绿长发和细剑；不要改变脸型、发型、服装和武器；无文字，无 UI，无水印。",
      "action": {
        "start": "细剑已出鞘，剑尖斜指地面",
        "middle": "缓慢抬剑至胸前，披风被风吹起",
        "end": "剑尖斜指前方，抬眼看向镜头"
      },
      "camera": "slow push-in, eye level, 16:9",
      "mode": "first_frame",
      "duration": 5,
      "resolution": "720p",
      "ratio": "16:9",
      "seed": 20261125,
      "generate_audio": false
    }
  ]
}
```

## 字段规则

| 字段 | 必填 | 规则 |
|---|---|---|
| `shots[].id` | 是 | 稳定 ID，如 `S01`；输出文件用它命名 |
| `story` | 是 | 镜头级剧情，不要只写“好看” |
| `reference_images` | `first_frame` 且无现成 keyframe 时必填 | 原画/参考图，1–10 张 |
| `keyframe` | 是 | 帧图输出路径；`mode=first_frame` 必须有 |
| `keyframe_prompt` | 无 keyframe 时必填 | 先定构图、服装、光线、背景；不写动作 |
| `video_prompt` | 是 | 写动作、镜头、连续性；必须和 `action` / `camera` 一致 |
| `action` | 是 | `start` / `middle` / `end` 三段，防模型乱动 |
| `camera` | 是 | 推/拉/摇/固定；不要只写“电影感” |
| `mode` | 否 | `first_frame`（默认）/ `reference` / `text` |
| `duration` | 是 | 4–30 秒；2.5 flash 也支持 30 秒 |
| `resolution` | 是 | 2.5 flash：`480p`/`720p`；2.5 全量：再加 `1080p`/`4k` |
| `ratio` | 是 | `16:9` 默认；2.5 首帧会由引擎改成 `adaptive` |
| `seed` | 是 | 固定整数；禁止 `-1`，避免随机抽卡 |
| `generate_audio` | 否 | 默认 `false`；要测音频再开 |

## 想法来源（硬规则）

- 镜头、景别、机位、运镜、动作编排、节奏、时长、转场、特效、负面词、提示词结构，都从 `skills/真人漫剧打斗 skill/` 取，并在回复里标出处。
- 技能库按文件读取，不通过 skill 工具调用。
- 技能库没写的，先停下来问用户，或标“待补充”，不要自己发明。
- 先填 `DemoStart.md` 的 8 项约束，再选方法。
- 方法文件：4 秒单条 → `分镜约束/分镜时长约束/4s-single-shot.md`；15 秒 → `15s-anime.md`；30 秒一镜 → `30s-one-take.md`；30 秒八段 → `30s-eight-segment.md`；系列 → `分镜时长约束.md` §2；大招 → `特别分镜/修仙-玄幻-魔法大招.md`。
- 七原则：`分镜约束/分镜内容约束/00-overview.md`；词库：`分镜材料库/`；骨架：`第三方模板/01-prompt-skeletons/`；案例：`第三方案例/EXAMPLES.md`；风格：`画面风格/画面风格.md`。
- F 木版画机位：4 秒单条用固定机位/轻微平移；30 秒一镜用手持跟拍（和纸质感的轻微呼吸微抖，不写 35mm/胶片/皮肤纹理）。
- 同一目标有多种方法时，先把方法列成可点击选项让用户选；选项写清方法名、方法文件、时长/段数、切镜方式、稳定性/风险。

## 三段闸门（硬规则）

> 用户原话：
> 1. 你先输出提示词给我判断
> 2. 合格之后你做帧，交给我判断
> 3. 合格之后得到我的允许你再去做视频

| 闸门 | 交付物 | 通过条件 | 不通过怎么办 |
|---|---|---|---|
| 1. 提示词 | `keyframe_prompt` + `video_prompt` 原文 | 用户明确说“通过 / 可以 / 继续” | 改 prompt，再发一次；不调用 API |
| 2. 帧图 | `build/<id>_keyframe.png`，逐张侧边栏打开 | 用户明确确认帧图 | 改 prompt / 换 reference，`--force-keyframe` 重出 |
| 3. 视频 | `build/<id>.mp4`，逐条侧边栏打开 | 帧图已通过 + 用户明确允许 | 改 `video_prompt` / `action`，`--force` 重跑 |

- 用户没有明确批准时，一律视为未批准；说“改”就退回上一步。
- 闸门由 Agent 执行；`render.py` 只负责 dry-run、`--yes`、`--force`，不判断用户是否已批准。
- 每生成一张帧图或一条视频，立即用 `browser.preview` 在 opencode 侧边栏打开，再等判断；不要只发路径。

## 生成流程

### 1. 先校验，不花钱

```powershell
python workspaces/vibe-knowledge/line/fe-gba/preflight.py `
  workspaces/vibe-knowledge/projects/<work>/lessons/<lesson>/work.json
```

它会检查：字段、原画是否存在、模型/分辨率是否匹配、seed 是否固定、输出是否已存在。

### 2. 提示词闸门：先给用户看 prompt

把每条镜头的 `keyframe_prompt` 和 `video_prompt` 原文发给用户，等明确批准。

- 不要只说“我写好了”，要把原文逐条贴出来。
- 用户说“改”就改 prompt 再发；没批准不调用 Seedream。
- 用户没有明确说“通过 / 可以 / 继续”时，视为未批准。

### 3. 帧图闸门：只出帧图

```powershell
python project.py render <work> --line fe-gba --yes --keyframe-only
```

每出一张立即在侧边栏打开，再等判断：

```text
browser.preview({ path: "projects/<work>/lessons/<lesson>/build/S01_keyframe.png" })
```

底层调用：

```text
ark.py image --model doubao-seedream-5-5-261028
  --prompt <keyframe_prompt>
  --reference <reference_images...>
  --size 2560x1440
  --out build/S01_keyframe.png
```

帧图必须人工确认：

- **帧图就是 `action.start`**：拔剑动作的帧图里剑必须在鞘中/手握剑柄；帧图已出鞘，动作只能写抬剑/前指
- 脸、发型、服装、武器和原画一致
- 16:9，人物不裁脚/不裁头
- 背景有剧情信息，不是纯白底
- 无文字、UI、水印

不过就改 `keyframe_prompt` / 换 reference，`--keyframe-only --force-keyframe --yes` 重出。**帧图不过，不进视频。**

### 4. 视频闸门：拿到许可再出视频

只有“帧图通过 + 用户明确允许”后才跑：

```powershell
python project.py render <work> --line fe-gba --yes --shot-id S01
```

每出一条立即在侧边栏打开，再等判断：

```text
browser.preview({ path: "projects/<work>/lessons/<lesson>/build/S01.mp4" })
```

底层调用：

```text
ark.py video --model doubao-seedance-2-5-flash-261115
  --prompt <video_prompt>
  --first-frame build/S01_keyframe.png
  --duration 5 --resolution 720p --ratio 16:9
  --seed 20261125
  --out build/S01.mp4
```

2.5 系列首帧模式会自动 `ratio=adaptive`；这是官方限制，不是 bug。

### 5. QA

```powershell
python project.py qa <work>
# 或直接跑产线脚本：
python workspaces/vibe-knowledge/line/fe-gba/qa.py <lesson> --root projects/<work>
```

输出：

- `build/S01_contact.jpg`：每秒一帧的接触表
- 时长、分辨率、fps 检查
- 缺文件/时长为 0 会报错

## 验收清单

- [ ] 每个镜头设计能指到 `skills/真人漫剧打斗 skill/` 的具体文件和段落
- [ ] `preflight.py` 通过
- [ ] 提示词闸门已通过：用户看过 `keyframe_prompt` / `video_prompt` 原文并明确批准
- [ ] 帧图闸门已通过：帧图逐张在侧边栏打开，用户明确确认帧图
- [ ] 视频闸门已通过：帧图通过后，用户明确允许再生成视频
- [ ] 帧图 = `action.start`（拔剑则剑在鞘中；已出鞘则动作不是拔剑）
- [ ] 帧图已确认：脸、发色、服装、武器与原画一致
- [ ] 帧图是 16:9，人物完整，背景有剧情
- [ ] 视频从首帧开始，动作符合 `action.start/middle/end`
- [ ] 镜头运动符合 `camera`
- [ ] 视频中没有文字、UI、logo、水印
- [ ] 时长/分辨率/fps 符合预期
- [ ] 接触表没有明显跳帧、脸崩、手崩、武器变形
- [ ] 每张帧图/每条视频生成后都在侧边栏打开过
- [ ] 只生成了 1 条；如果要重跑，已记录原因并显式 `--force`

## 失败处理

| 现象 | 处理 |
|---|---|
| 帧图服装不对 | 改 `style_lock` / `keyframe_prompt`，换更清晰的原画；`--keyframe-only --force-keyframe --yes` 重出 |
| 帧图与动作起点不一致 | 改帧图（如剑入鞘）或改 `action`；不要硬让模型“凭空拔剑” |
| 帧图背景太空 | 在 `keyframe_prompt` 写清地点、前景/中景/远景、光线 |
| 视频脸漂 | 回退到帧图，缩短 `duration`，加强“保持脸型/发型”约束 |
| 视频动作乱 | 只改 `video_prompt` / `action`，不要改 seed；`project.py ... --shot-id S01 --force --yes` |
| API 400 | 先看分辨率/时长/模型是否匹配；2.5 flash 不支持 1080p/4k |
| API 429 | 等 30–60 秒；不要连续重试 |
| 输出已存在 | 默认跳过；视频加 `--force`，帧图加 `--force-keyframe`；不要无脑覆盖 |

## 不要做

- 不要跳过闸门：提示词没批不生成帧图，帧图没批不生成视频。
- 不要生成完只发路径；每张帧图/每条视频都要在侧边栏打开。
- 不要用 `seed: -1` 反复抽卡。
- 不要自动重试、自动改 prompt、自动换模型。
- 不要把带站名/水印的原画直接当首帧。
- 不要把 `keyframe` 和 `reference` 混用：Seedance 的首帧/首尾帧与全模态参考是互斥场景。
- 不要在 `work.json` 里写绝对路径。
- 不要在没有 `--yes` 的情况下以为已经生成；默认是 dry-run。

## 最小样例与冒烟

```powershell
python workspaces/vibe-knowledge/line/fe-gba/smoke_test.py
```

冒烟测试会创建临时项目、生成占位图、跑 `preflight.py` 和 `render.py` 的 dry-run；**不调用付费 API**，结束后清理。
