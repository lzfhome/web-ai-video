# poetry

一句话：**书封就是画面，文字是代码排的，BGM 是你选的。**

> 想要「有配音」的版本，用 `line/poetry-tts/`：版式、字段一样，只多一个 `voice`，每场时长由配音决定。

## 画面怎么来的

- **背景、书封、雾、光斑、浮尘、暗角、颗粒**：DOM/CSS。
- **诗句、署名、角标**：DOM。字是浏览器字体渲染，锐利、可排版。
- 没有任何 WebGL / canvas 绘制，也没有 AI 素材。

## 怎么用（3 步）

1. 把这一轮要用的封面 / BGM 放进 `line/poetry/assets/`
2. 打开 `line/poetry/build.json`：每个参数旁边都有中文说明，照着改
3. 让 agent 跑 `python project.py build poetry`

跑完会在 `workspaces/vibe-knowledge/projects/<id>/` 生成一个新项目：

```text
projects/<id>/
├── project.json
├── lessons/<id>/
│   ├── film.js          # 自动复制，不用改
│   ├── poem.json        # 由 build.json 生成的快照
│   └── assets/          # 封面和 BGM 的副本
└── deliveries/<日期>_v1/
    ├── video.mp4
    └── cover.jpg
```

`build.json` 里的 `id` 决定文件夹名。重名时自动加 `-v2`、`-v3`。
所以「再写一条诛仙」就是改一下 id 再跑一次，旧的那条不受影响。

## 默认风格

| 项 | 默认 |
|---|---|
| 背景 | 同一张书封放大 3.3 倍、`blur(7px)`、压暗 |
| 版式 | 左书右字，书 430×606，字 70px 楷体 |
| 入画 | 书封先淡入 1.3s → 诗句 2.1s / 2.9s → 署名 4.3s |
| 氛围 | 冷雾 + 虚焦光斑 8 颗 + 浮尘 46 + 颗粒 |
| 节奏 | 每场 15s，场间 0.95s 淡黑 |
| BGM | 整片一首，淡入 2.4s，淡出 3s |

## build.json

**每个参数旁边都有中文注释**，直接打开 `line/poetry/build.json` 看就行——它支持 `//` 注释，改完保存即可。
下面这张表只是速查索引。

### 顶层

| 字段 | 默认 | 说明 |
|---|---|---|
| `id` | `poetry` | 项目文件夹名，也是成片 id |
| `title` | `id` | 交付标题 |
| `fps` | `30` | 帧率 |
| `poster` | `7` | 交付封面取第几秒 |
| `font` | `kai` | `kai` 楷体 / `song` 宋体 / `sans` 黑体 |
| `scene_seconds` | `15` | 每场时长，可被场景的 `seconds` 覆盖 |
| `transition` | `0.95` | 场尾淡黑时长 |
| `palette` | `jade` | 全局调色板 |
| `type` | `{size:70, source_size:19, tracking:4, credit_ratio:0.6, footer_size:18}` | 字号 / 字距；`credit_size` 不写就按 `size × credit_ratio` 自动跟随 |
| `gap` | `{image_in:1.3, text1:2.1, text2:2.9, credit:4.3, text_dur:1.2, credit_dur:1.1, rise:14}` | 入场时间（场景内秒）；`credit` 改成和 `text1` 一样，署名就和主句同拍出现 |
| `effects` | 见 `build.json` 注释 | 光斑 / 浮尘 / 雾 / 颗粒 / 暗角 / 书封光晕 / 镜头推近 / 字柔光，每一项都能单独调 |
| `book` | `{x:132, y:148, w:430, h:606, tilt:-1.8}` | 书封位置 / 大小 / 倾斜 |
| `bgm` | — | 配乐，见下 |
| `scenes` | — | 场景数组，一场一个对象 |

### bgm

```json
"bgm": {
  "src": "resources/music/xxx.mp3",
  "from": 0,
  "gain_db": -13,
  "fade_in": 2.4,
  "fade_out": 3.0
}
```

`src` 可以写 `assets/xxx.mp3`（相对 `line/poetry/`），也可以写 `resources/...`（相对 AIWork 根目录），或绝对路径。
运行时会复制进项目。

### scenes[]

| 字段 | 默认 | 说明 |
|---|---|---|
| `cover` | — | **必填**，`assets/cover-1.jpg` 或绝对路径 |
| `line1` | — | 第一行（或改用 `lines`） |
| `line2` | — | 第二行 |
| `lines` | — | 多行数组，优先于 `line1/line2`；每行一条，逐行错开淡入 |
| `type` | 顶层 | 单场字号覆盖，如 `{"size": 46}` |
| `palette` | 顶层 | 这一场的调色板 |
| `seconds` | `scene_seconds` | 这一场多长 |
| `blur` | `7` | 背景虚化 px，4–14，低于 4 会看到 JPEG 块 |
| `brightness` | `0.5` | 背景亮度，火/亮色封面用 0.42 |
| `saturate` | `0.95` | 背景饱和度 |
| `flip` | `false` | 背景水平镜像，把封面主体挪开文字区 |
| `credit` | — | 署名 |
| `source` | — | 出处 |
| `header` | — | 右上角小字 |
| `footer` | — | 左下角说明 |
| `book` | 顶层 | 单场覆盖书封位置 |
| `effects` / `gap` | 顶层 | 单场覆盖 |
| 调色板键 | — | `text` `halo` `rain` … 可在场景里单点覆盖 |

### 调色板

| 名字 | 观感 | 适合 |
|---|---|---|
| `jade` | 青绿冷雾 | 山水、仙侠、旧版书封 |
| `ember` | 火光暖褐 | 战斗、焚城、血色场景 |
| `moon` | 蓝夜月白 | 夜景、离别、回忆 |
| `ink` | 墨黑宣纸 | 纯文字、书法、悼亡 |

可覆盖的键：
`base` `tint` `radial` `mistA` `mistB` `rain` `rainGlow` `rainHead` `bokeh`
`dustCool` `dustWarm` `halo` `text` `credit` `sourceColor` `headerColor` `tab`

## 调参速查

| 想要 | 改 |
|---|---|
| 背景更实 | `scenes[].blur` 7 → 5 |
| 背景更虚 | `blur` 7 → 10~14 |
| 背景更亮 | `brightness` 0.5 → 0.58 |
| 光斑更多 / 更大 / 浮得更快 | `bokeh` / `bokeh_size` / `bokeh_rise` |
| 浮尘更多 / 更粗 / 更亮 | `dust` / `dust_size` / `dust_glow` |
| 雾更浓 / 漂得更快 | `mist` / `mist_speed` |
| 四角更暗 / 颗粒更重 | `vignette` / `grain` |
| 书封光晕 / 封面高光 | `halo` / `sweep` |
| 镜头推近 / 背景横移 | `zoom` / `drift` |
| 字更柔 | `text_glow` |
| 左下角出处行更大 / 更小 | `type.footer_size`（默认 18） |
| 字更大 / 更松 | `type.size` / `type.tracking` |
| 署名更大 / 更小 | `type.credit_size`（不写就自动 = 主句 × 0.6） |
| 字更早出现 | `gap.text1` / `gap.text2` |
| 署名和主句同拍 | `gap.credit` 设成和 `gap.text1` 一样 |
| 出处更早 / 更晚 | 跟署名共用 `gap.credit` |
| 每场更长 | `scene_seconds` |
| 黑场更长 | `transition` |
| BGM 从副歌进 | `bgm.from` |
| BGM 更轻 | `bgm.gain_db` |

## 换一本小说

这条产线就是模板：**代码不动，只换 `build.json` 和封面。**

按顺序改这几处：

| 步骤 | 改什么 | 例子 |
|---|---|---|
| 1 | `id` / `title` | `"id": "san-ti-10"`、`"title": "三体 · 十句话"` |
| 2 | `scenes[].cover` | `"assets/santi-1.jpg"`，图放 `line/poetry/assets/` |
| 3 | `scenes[].lines` | 原文，多行就写数组；每行建议 ≤ 14 字 |
| 4 | `scenes[].credit` / `source` | 人 / 章号+章名 |
| 5 | `scenes[].header` / `footer` | 右上角卷号、左下角出处 |
| 6 | `scenes[].palette` | `jade` `ember` `moon` `ink` 四选一 |
| 7 | `bgm.src` | 换成这一轮的曲子 |

剩下的 `type` / `gap` / `effects` / `book` 不用动，除非画面不对。

**字号怎么定**：主句默认 66–70px，一行大约 13–14 字；
句子长就按场调小（`"type": {"size": 50}`），4 行以上建议 46–54。

**封面要求**：宽度 ≥ 600px；低于这个数 `blur` 不要低于 5，否则放大后有噪点。

然后让 agent 跑 `python project.py build poetry`。旧项目不动，新片落在 `projects/<新 id>/`。

需要配音的版本用 `line/poetry-tts/`，字段一样，多一个 `voice`；见 `line/poetry-tts/README.md`。

## 注意

- `projects/<id>/lessons/<id>/poem.json` 是**快照**，下次出片不会读它；要改内容改 `line/poetry/build.json`
- 书封原图建议 ≥ 600px 宽；400×576 放大到 1920 有插值噪点，所以 `blur` 不要低于 4
- 想更实可以先超分封面，再放进 `assets/`
- 交付封面用 `poster`，一般取第 7 秒（第一场）或第 22 秒（第二场）
- BGM 版权状态不因 `user_request` 改变，发布前按平台规则确认
