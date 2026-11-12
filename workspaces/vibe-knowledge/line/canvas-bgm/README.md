# canvas-bgm

纯 Canvas 画面 + BGM，没有旁白。出片最快的产线：30 秒片约 10 秒渲完。

## 什么时候用

- 文字、图表、关键词、计数、频谱、简单动效
- 不需要旁白，靠 BGM 和字幕撑节奏
- 需要快速迭代（改一行代码就能重渲）

需要复杂 CSS 排版、3D、旁白时，改用 `dom-narrated`。

## 内容文件

```text
lessons/<lesson>/
├── film.canvas.js      # 唯一要改的文件
└── assets/img/         # 用到的图片
```

`film.canvas.js` 必须导出：

| 导出 | 类型 | 说明 |
|---|---|---|
| `duration` | number | 成片时长（秒） |
| `fps` | number | 帧率，一般 30 或 60 |
| `images` | object | `{ key: "img/x.png" }`，引擎预加载 |
| `build(c)` | function | 返回镜头数组 |

`build(c)` 返回：

```js
[{ from: 0, to: 5, draw(t, c) { /* 画 t 这一帧 */ } }]
```

`t` 是绝对秒。`c` 是画布上下文工具，组件在 `cine/video/engines/canvas/components.js`。

可用组件：`bg`、`title`、`keyword`、`counter`、`bars`、`plate`、`foot`、`chapter`、`progress`、`spectrum`、`waves`。

## BGM

默认 `resources/music/vibe-bgm.m4a`。`--no-bgm` 关掉。

## 渲染

```powershell
python project.py render <work> --line canvas-bgm
python project.py render <work> --line canvas-bgm --fps 60
python project.py render <work> --line canvas-bgm --no-bgm
```

## 注意

- 只能画 Canvas 2D 能画的东西；DOM/CSS 的排版、字体细节这里做不到
- 没有旁白时间轴，`narration.json` 不参与
- 参考作品：`projects/sky-blue`

## 相关代码

- 引擎：`cine/video/engines/canvas/engine.js`（WebCodecs + Mediabunny）
- 组件：`cine/video/engines/canvas/components.js`
- 渲染入口：`line/canvas-bgm/render.py`
