# cine/video/engines/canvas

Canvas 2D + WebCodecs 快速通道。30 秒片约 10 秒渲完，比 DOM 引擎快一个数量级。

## 原理

页面里逐帧画 Canvas，用 WebCodecs 编码成 H.264，再通过 Mediabunny 封装成 MP4，整个视频在浏览器里生成，不需要逐帧截图。

## 文件

| 文件 | 作用 |
|---|---|
| `index.html` | 入口页，加载 `engine.js` |
| `engine.js` | `boot()`：读 `?film=`、等图片、逐帧 `draw`、编码、返回 base64 MP4 |
| `components.js` | 绘制组件：`bg`、`title`、`keyword`、`counter`、`bars`、`plate`、`foot`、`chapter`、`progress`、`spectrum`、`waves` |
| `vendor/mediabunny.js` | MP4 封装（MPL-2.0） |

## 契约

`film.canvas.js` 必须导出：

```js
export const duration = 30;
export const fps = 30;
export const images = ["img/a.png"];
export function build(c) {
  return [{ from: 0, to: 5, draw(t, c) {} }];
}
```

`c` 里有 `canvas`、`ctx`、`W`、`H`、`t`、`img(src)`。

## 谁在用

- `line/canvas-bgm/render.py`

## 注意

- 只能画 Canvas 能画的东西；字体排版、CSS 滤镜这里没有
- 画布固定 1920×1080，`devicePixelRatio` 不参与
- 编码质量默认 20 Mbps，`--quality` 可调
