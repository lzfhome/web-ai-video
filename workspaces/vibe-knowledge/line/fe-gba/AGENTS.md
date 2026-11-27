# fe-gba · GBA 火焰纹章镜头线

一句话：**官方原画定角色，打斗技能库定镜头/动作/节奏，帧图定构图；提示词 → 帧图 → 视频，三段都要用户点头；一条镜头只跑一次。**

## 适用

- GBA 火焰纹章三作：封印之剑 / 烈火之剑 / 圣魔之光石
- Seedance 2.5 flash 的 5–30 秒单镜头测试、角色一致性测试、动作测试
- 需要“原画参考 → 关键帧 → 视频”的可复现流程

不适用：整片自动剪辑、纯图片、非火纹题材。整片仍走 `dom-narrated` / `poetry` 等产线。

## 想法来源（硬规则）

- 所有创作决定——镜头、景别、机位、运镜、动作编排、节奏、时长、转场、特效、负面词、提示词结构——必须来自 `skills/真人漫剧打斗 skill/` 的具体文件，并在回复里标出处（文件 + 小节）。
- 技能库按文件读取（路径见下表），不通过 skill 工具调用。
- 禁止“我觉得”“为了稳”“一般这样更好”这类个人发明；技能库没写的，先停下来问用户，或标“待补充”，不要自己补。
- 先填 `DemoStart.md`（8 项约束：项目 / 时长 / 画幅 / 风格 / 人物 / 场景 / 动作 / 声音），再进方法。
- 选方法读 `分镜约束/分镜时长约束/分镜时长约束.md`，按任务查表：

| 任务 | 方法 | 骨架 |
|---|---|---|
| 4 秒单条、1–2 个动作、切镜后期 | `分镜约束/分镜时长约束/4s-single-shot.md` | `第三方模板/01-prompt-skeletons/4s.md` |
| 15 秒二次元、连招/角色签名 | `分镜约束/分镜时长约束/15s-anime.md` | `第三方模板/01-prompt-skeletons/15s.md` |
| 30 秒一镜到底、21 拍 | `分镜约束/分镜时长约束/30s-one-take.md` | `第三方模板/01-prompt-skeletons/30s-one-take.md` |
| 30 秒八段、3–4 秒/段 | `分镜约束/分镜时长约束/30s-eight-segment.md` | `第三方模板/01-prompt-skeletons/30s-eight-segment.md` |
| 系列（60 秒以上 / 多集） | `分镜约束/分镜时长约束/分镜时长约束.md` §2「系列」 | — |
| 修仙/玄幻/魔法大招 | `特别分镜/修仙-玄幻-魔法大招.md` | `第三方模板/01-prompt-skeletons/ultimate.md` |

- 技能库按这个顺序用：

| 顺序 | 目录 / 文件 | 作用 |
|---|---|---|
| 1 | `DemoStart.md` | 任务简报，先定 8 项约束 |
| 2 | `分镜约束/分镜时长约束/` | 4 秒 / 15 秒 / 30 秒一镜 / 30 秒八段 / 系列 / 大招 |
| 3 | `分镜约束/分镜内容约束/` | 七原则：因果 / 节奏 / 镜头 / 物理 / 连续性 / 可读性 / 禁忌 |
| 4 | `分镜材料库/` | 动作 / 镜头 / 特效 / 风险 / 风格 / 一致性词库 |
| 5 | `第三方模板/` | 提示词骨架 / 脚本 / 表单 |
| 6 | `第三方案例/` | 示例 / 成片 / 插入 / 资产 / 参考提示词 |
| 7 | `画面风格/画面风格.md` | 介质 / 画幅 / 平台 / 风格替换 |
| 8 | `特别分镜/` | 大招等特殊分镜 |

- `模型习惯/1.md` 是 Seedance 2.0 的短剧导演提示词（默认 9:16、15 秒、最多 5 镜头），只能当 2.0 参考；`fe-gba` 用 2.5、16:9、4 秒素材，不能照搬它的参数。
- F 木版画机位：4 秒单条用固定机位/轻微平移；30 秒一镜用手持跟拍（和纸质感的轻微呼吸微抖，不写 35mm/胶片/皮肤纹理）。
- 场景不是分类轴：先写在 `DemoStart.md` §6，再查 `分镜材料库/06-style/` 和 `画面风格/画面风格.md`；案例只在 `第三方案例/`。
- **同一目标有多种方法时，先把方法列成可点击选项让用户选，不要替用户选。** 选项必须写清：方法名、方法文件、时长/段数、切镜方式、稳定性/风险。
- 选定方法后，再读对应方法和模板骨架，不凭印象写。
- 用户指令和技能库冲突时，先指出冲突，由用户决定；不要用个人偏好覆盖技能库。
- 工程实现（ffmpeg、API、渲染命令）不属于“创作想法”，但参数选择也要优先服从技能库的格式约束。

## 三段确认（硬规则，不得跳步）

> 用户原话：
> 1. 你先输出提示词给我判断
> 2. 合格之后你做帧，交给我判断
> 3. 合格之后得到我的允许你再去做视频

1. **提示词闸门**：先把本 lesson 每条镜头的 `keyframe_prompt` 和 `video_prompt` 原文发给用户；用户明确说“通过 / 可以 / 继续”之前，不调用 Seedream，也不调用 Seedance。
2. **帧图闸门**：提示词通过后，只跑 `--keyframe-only` 出帧图；每出一张立即在 opencode 侧边栏打开；用户明确确认帧图之前，不生成任何视频。
3. **视频闸门**：帧图通过、且用户明确允许后，才生成视频；一条镜头只跑一次，重跑必须 `--force`。
4. 用户说“改”就回到上一步改 prompt / 帧图，不进入下一步；用户没有明确批准时，一律视为未批准。
5. 闸门由 Agent 执行；`render.py` 只负责 dry-run、`--yes`、`--force`，不判断用户是否已批准。

## 每次生成都在侧边栏打开（硬规则）

- 每生成一张帧图：立即用 `browser.preview` 在 opencode 侧边栏打开该 PNG，并把路径发给用户。
- 每生成一条视频：立即在侧边栏打开该 MP4，并把路径发给用户。
- 批量跑完也要逐条打开，不要只报一句“完成了”；用户没看之前不要进入下一步。

## 强制流程

1. **写 `work.json`**：先写故事、镜头、动作、镜头运动、角色锁定，再写 prompt。
2. **准备原画**：放到 `lessons/<lesson>/assets/`，文件名写进 `reference_images`。
3. **preflight**：跑 `preflight.py`，确认字段、模型、seed、输出路径。
4. **提示词闸门**：把每条 `keyframe_prompt` / `video_prompt` 原文发给用户，等明确批准。
5. **帧图闸门**：只出帧图，逐张在侧边栏打开，等用户确认。
   - **帧图必须等于 `action.start`**：动作是拔剑，帧图里剑就得在鞘中；帧图已经出鞘，动作就写抬剑/前指，不能写拔剑。
6. **视频闸门**：帧图通过并拿到许可后，才以帧图为 `first_frame` 生成视频。
7. **QA 抽帧**：跑 `qa.py` 看时长、分辨率、接触表；不过就改描述，不靠重抽。

## 一条镜头只跑一次（硬规则）

- `defaults.json` 的 `max_takes` 固定为 `1`。
- `render.py` 默认 **dry-run**；不加 `--yes` 不调用付费 API。
- 输出已存在时默认跳过；重跑视频要显式 `--force`，重出帧图要显式 `--force-keyframe`。
- 不自动重试、不自动改 prompt、不自动换 seed。
- seed 默认固定为 `20261125`；`preflight.py` 拒绝 `seed: -1` 的“随机抽卡”配置。

## 目录

```text
workspaces/vibe-knowledge/line/fe-gba/
├── AGENTS.md
├── TEMPLATE.md
├── defaults.json
├── schema.json
├── work.skeleton.json
├── preflight.py       # 校验 work.json，打印计划；不花钱
├── render.py          # 帧图 → 视频；默认 dry-run
├── qa.py              # ffprobe + 接触表
├── smoke_test.py      # 不调用 API 的冒烟测试
└── examples/
    └── eirika.work.json

projects/<work>/lessons/<lesson>/
├── work.json          # 唯一输入
├── assets/            # 原画 / 参考图
└── build/             # keyframe、mp4、接触表
```

## 命令（从仓库根目录）

```powershell
# 1. 只校验并看计划，不花钱
python workspaces/vibe-knowledge/line/fe-gba/preflight.py projects/<work>/lessons/<lesson>/work.json

# 2. dry-run：打印将执行的 Seedream / Seedance 命令
python project.py render <work> --line fe-gba

# 3. 提示词闸门通过后：只生成帧图，逐张在侧边栏打开
python project.py render <work> --line fe-gba --yes --keyframe-only
#    也可以一条一条来，方便逐张确认：
python project.py render <work> --line fe-gba --yes --keyframe-only --shot-id S01

# 4. 帧图闸门通过并拿到许可后：再生成视频，逐条在侧边栏打开
python project.py render <work> --line fe-gba --yes --shot-id S01

# 5. 审片（project.py 会设置 CINE_ROOT）
python project.py qa <work>
```

每次生成后立即在 opencode 侧边栏打开（不要只发路径）：

```text
browser.preview({ path: "projects/<work>/lessons/<lesson>/build/S01_keyframe.png" })
browser.preview({ path: "projects/<work>/lessons/<lesson>/build/S01.mp4" })
```

`project.py render` 在 `fe-gba` 下默认 dry-run；只有 `--yes` 才会调用付费 API。  
直接跑产线脚本也可以：

```powershell
$env:CINE_ROOT="workspaces/vibe-knowledge/projects/<work>"
python workspaces/vibe-knowledge/line/fe-gba/render.py <lesson> --yes --shot S01
```

## 角色与原画约定

- 原画只作**参考/首帧来源**，不要直接把带水印、带站名、带 UI 的图喂给模型。
- 同一镜头里角色服装、发色、武器必须写进 `style_lock` 和 `video_prompt`。
- 需要“原画感”时写：`GBA 火焰纹章官方插画风格、赛璐璐上色、清晰轮廓、复古奇幻色调`。
- 不要让模型生成文字、UI、logo、水印；这些由后期代码处理。

## 失败处理

- 帧图不对：改 `keyframe_prompt` / 换 reference → `--keyframe-only --force-keyframe --yes`。
- 首帧对、视频动作不对：只改 `video_prompt` / `action` / `camera` → `project.py ... --shot-id S01 --force --yes`（直接跑 render.py 时用 `--shot S01`）。
- 视频动作对、脸漂：回到帧图，或缩短 `duration`；不要靠反复抽卡。
- API 报错：保留 `work.json` 和命令行输出，先解决参数/模型问题，再重跑。

## 相关

- 详细字段、样例、验收清单：`TEMPLATE.md`
- 模型：`doubao-seedance-2-5-flash-261115`（默认）/ `doubao-seedance-2-5-260628`
- 帧图：`doubao-seedream-5-5-261028`
- API 客户端：`cine/image/engines/ark.py`
