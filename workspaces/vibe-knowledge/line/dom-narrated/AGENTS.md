# dom-narrated

DOM/CSS + Three.js 画面 + 旁白 + BGM。视觉上限最高，速度比 Canvas 慢（30 秒片约 1–2 分钟）。

## 什么时候用

- 需要旁白（TTS）和字幕
- 需要复杂排版、CSS 动画、风格模板
- 需要 3D 场景、后期辉光、镜头运动
- 想做「知识讲解」而不是「字卡」

不需要旁白、只要快，用 `canvas-bgm`。

## 内容文件

```text
lessons/<lesson>/
├── film.js          # 画面与时间轴
├── narration.json   # 旁白 / 字卡时间轴
├── facts.md         # 事实与出处
└── assets/
```

### narration.json

```json
{
  "mode": "silent",
  "beats": [
    { "id": "B01", "dur": 6.5, "card": "标题" },
    { "id": "B02", "dur": 8.0, "card": "第二段" }
  ]
}
```

- `mode: silent`：无旁白，只生成时间轴和静音轨（`cine/audio/engines/tts_silent.py`）
- `mode: edge`：用 edge-tts 配音，`voice` 里写 `{"engine":"edge","voice":"zh-CN-YunxiNeural","rate":"+8%","pitch":"-2Hz"}`
- `mode: doubao`：用豆包语音合成 2.0 配音，`voice` 里写 `{"engine":"doubao","voice":"zh_male_qingcang_uranus_bigtts","speed":0.92}`（或渲染时加 `--tts doubao`）

三种都会生成 `build/timings.json` 和 `build/narration.wav`。

### film.js

必须导出：

| 导出 | 说明 |
|---|---|
| `COLD` | 冷开场秒数，一般 0 |
| `TAIL` | 旁白结束后多留几秒 |
| `meta` | `{ title, n }` |
| `music` | BGM 数组，`build()` 里 push |
| `build(ctx)` | 返回镜头数组 |

可选：`hits`（冲击点）、`blur`（转场模糊点）、`clips`（叠加片段）、`sfx`、`sections`、`COLD_SRC`（用现成片段做片头）。

镜头结构：

```js
{
  from: 0, to: 6,
  build(root) { /* 建 DOM，返回 ui 对象 */ },
  render(t, ui) { /* 按绝对秒 t 更新 */ }
}
```

`ctx` 里有 `W`、`H`、`THREE`、`narr`（`total` / `at()` / `sub()`）。

## 风格模板

`resources/styles/` 下有 46 套风格，每套一个目录：

```text
resources/styles/<name>/
├── STYLE.md      # 配色、字体、动效规则
└── still.jpg     # 样片截图
```

索引：`resources/styles/INDEX.md`、`resources/styles/catalog.json`。

## 渲染

```powershell
python project.py render <work> --workers 2
python project.py render <work> --workers 2 --fps 60
python project.py render <work> --workers 2 --from 12 --to 20   # 只渲一段
python project.py render <work> --audio-only                    # 只重混音
```

## 注意

- `--workers 4` 在这台机器上偶发浏览器实例起不来，默认用 2
- 改了 `film.js` 但 `build/timings.json` 已存在时，不会自动重算旁白；要重算先删 `build/timings.json`
- 参考作品：`projects/sangetsuki`、`projects/benford`

## 相关代码

- 引擎入口：`cine/video/engines/dom/core.js`
- 录制：`cine/video/engines/dom/record.py`、`stills.py`
- 音轨：`line/dom-narrated/finish.py`
- 组件库：`cine/video/engines/dom/know.js`、`ui.js`
