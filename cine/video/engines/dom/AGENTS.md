# cine/video/engines/dom

DOM/CSS + Three.js 渲染引擎。一条片 = 一个 `seek(t)`：给定秒数，画出那一帧。

## 入口

`core.js` 是页面入口（`index.html` 加载它）：

1. 读 `/lessons/<lesson>/build/timings.json`
2. `import` `/lessons/<lesson>/film.js`
3. `build(ctx)` 建好所有镜头
4. `seek(t)` 只显示当前镜头并调 `render(t, ui)`

支持的 URL 参数：`?t=12.5`（定帧）、`?play`（播放）、`?capture`（录制模式）、`?bridge=1`（外部逐帧驱动）。

## 文件

| 文件 | 作用 |
|---|---|
| `core.js` | 启动、seek、镜头切换、字幕层 |
| `util.js` | 时间、缓动、随机数、`el` / `css` |
| `narr.js` | 旁白时间轴：句子、cue、字幕 |
| `know.js` | 知识片组件库：`TH`、`bg`、`plate`、`keyword`、`counter`、`choice`、`vquote`、`trail`、`spread`、`chapter` 等 |
| `ui.js` | 通用 DOM 动效组件（出现、强调、打字） |
| `post.js` | 后期：HDR → 辉光 → ACES → 暗角 |
| `glsl.js` | GLSL 片段（3D simplex 噪声等） |
| `rpg-qa.js` | 像素问答引擎（旧组件，对应产线已删，代码保留） |
| `scenes/` | 3D 场景组件（见 `scenes/AGENTS.md`） |

## 录制工具

| 文件 | 作用 |
|---|---|
| `record.py` | 逐帧截图 → `build/picture.mp4`；`--workers N` 分段并行 |
| `stills.py` | 抽若干时间点做接触表 `stills/*.jpg` |
| `clips.py` | 把源视频切成叠加片段 `assets/clips/<id>.mp4` |
| `retail.py` | 只重渲某个 cue 之后的部分 |

```powershell
python cine/video/engines/dom/record.py <lesson> --fps 30 --workers 2
python cine/video/engines/dom/stills.py <lesson> out.jpg 7 22 --cols 2
```

## 镜头契约

```js
{
  from: 0, to: 6,
  build(root) { /* 建 DOM，返回 { s, ... } */ },
  render(t, ui, shot) { /* 按绝对秒更新 */ }
}
```

`ui.s` 是这个镜头的根节点，`core.js` 用它的 `display` 做切换。

## 注意

- 所有动画必须是时间 `t` 的纯函数，不能有内部状态；否则并行渲染会不一致
- 一帧的 DOM 越少越快；`filter: blur()` 和 `box-shadow` 多了会明显掉速
- three.js 从 `cine/vendor/` 走 importmap，不要另装
