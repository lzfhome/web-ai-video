# cine/video/engines/dom/scenes

DOM 引擎里的 3D 场景组件。都是 Three.js + GLSL，按「时间 t 的纯函数」写，可以逐帧确定性地渲染。

## 文件

| 文件 | 场景 |
|---|---|
| `particles.js` | 26 万粒子：爆炸、星云、标题粒子、水平线、尘埃 |
| `bars.js` | 200 根柱状频谱，高度 = 低频 + 中频 + 高频 |
| `clock.js` | 嵌套表盘 + 轨道 + 指针，转动取决于时间 |
| `liquid.js` | 7 个水滴融合的液态金属，可塌缩成一点 |
| `showroom.js` | 展台：轨道相机、反射地板、彩色灯带 |
| `tunnel.js` | 代码纹理贴在内壁的隧道，镜头加速穿过 |

## 用法

```js
import { Particles } from "../../cine/engine/scenes/particles.js";
```

在 `film.js` 的 `build(ctx)` 里创建，在 `render(t)` 里更新 uniform。

## 注意

- 这些是可视化组件，不含叙事；叙事逻辑留在 `film.js`
- 粒子数量大，`--workers` 并行时注意显存
- 需要 `three`，从 `cine/vendor/three.module.min.js` 走 importmap
