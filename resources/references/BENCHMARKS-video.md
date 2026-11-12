# 视频框架速度基准（2026-11-10）

同一台机器：i7-12700H / RTX 3060 Laptop / Windows 11。
测试片：30 秒，1920×1080，30fps，900 帧，文字 + 简单图形/图片。

## 当前引擎

| 配置 | 耗时 |
|---|---:|
| 单进程 + raw RGB 管道 | 约 73s（按 5s 实测换算） |
| 4 workers + raw RGB | 38s |
| 4 workers + JPEG 直通 | **21s** |

- 4 workers 质量：与单进程 SSIM 0.9956 / PSNR 50.9dB
- 6/8 个独立 Chrome 进程会卡页面加载，不可用

## Remotion 4.0.542

同一部 30 秒片，Remotion composition 内嵌 cine 页面，通过 postMessage 驱动 seek。

| 配置 | 耗时 |
|---|---:|
| 4 tabs, JPEG 80 | 33.1s |
| 8 tabs, JPEG 80 | 26.5s |
| 12 tabs, JPEG 80 | 25.1s |
| 16 tabs, JPEG 80 | 25.0s |
| 16 tabs, JPEG 95 | 30.9s |

画质（以当前引擎为基准）：

| Remotion | SSIM | PSNR |
|---|---:|---:|
| JPEG 80 | 0.9836 | 43.7dB |
| JPEG 95 | 0.9913 | 47.4dB |

结论：Windows 版 Remotion 没启用 shared-memory，仍走 `image2pipe` JPEG，速度慢于当前引擎。

证据：官方 npm 包 `@remotion/compositor-win32-x64-msvc@4.0.542` 的 `ffmpeg.exe` 不含 `remotionshm`；Linux 包 `ffmpeg` / `libavdevice.so` 含 `remotionshm` 和 `pool_dir`。

## Editly 5.6k

安装失败：

- 依赖 `gl` 原生模块没有 Node 18/22 的 Windows 预编译包
- node-gyp 需要 Visual Studio C++ Build Tools，当前机器未安装

结论：不装 VS Build Tools 无法测；不是速度问题。

## Motion Canvas 19.7k

- 官方没有 headless CLI；渲染是编辑器里的 RENDER 按钮
- 要自动化得用 Playwright 点 UI
- 本次未继续；不是它慢，而是没有可脚本化入口

## Revideo 4.2k

- 依赖安装约 364MB；Puppeteer 下载卡住
- 手动补 Chrome 156 后，Windows 上 `--single-process` 导致 frame detached
- 去掉 `--single-process` 后能渲染到 89%，但最终 `visuals.mp4` 无效，音频阶段报 `Invalid duration specification for t: N/A`
- 结论：Windows headless 渲染当前不稳定，未拿到有效成片

## Mediabunny 7.5k + WebCodecs（Canvas 直编）

不走截图：Canvas 2D 每帧直接进 `VideoEncoder`，Mediabunny 封装 MP4。

| 配置 | 耗时 | 文件 |
|---|---:|---:|
| 30s / 30fps / 900 帧 | **3.75s** | 12.2MB |
| 30s / 60fps / 1800 帧 | **6.67s** | 17.9MB |
| 30s/60fps 视频 + BGM mux | +0.70s | 18MB |

- Chrome 158 支持 `avc1.640028` 1080p WebCodecs 编码
- 画面检查：中文文字边缘干净，无截图/JPEG 压缩痕迹
- 限制：只能编码 Canvas/WebGL 内容；现有 `know.js` 的 DOM/CSS 文字要迁到 Canvas 2D/Skia

## Canvas 30 秒成片实测（不是裸 benchmark）

题目：天空为什么是蓝的；6 张卡 × 5 秒；文字 + 渐变 + 粒子 + 光谱条 + 正弦波 + 日落。

| 规格 | WebCodecs 渲染+编码 | BGM mux | 总计 | 成片 |
|---|---:|---:|---:|---:|
| 30s / 30fps / 900 帧 | 6.56s | 0.67s | **7.24s** | 33.5MB |
| 30s / 60fps / 1800 帧 | 9.43s | 0.66s | **10.09s** | 50.3MB |

成片：

- `out/sky-blue/2026-11-10_canvas-30s/video.mp4`
- `out/sky-blue/2026-11-10_canvas-30s_60fps/video.mp4`

## 正式 Canvas 组件通道（title/keyword/counter/bars/plate）

作品：`projects/sky-blue`，30 秒 BGM-only，6 张卡。

| 规格 | 渲染+编码 | BGM mux | 总计 | 帧数 |
|---|---:|---:|---:|---:|
| 30s / 30fps | 7.20s | 0.66s | **7.86s** | 900 |
| 30s / 60fps | 11.46s | 0.72s | **12.18s** | 1800 |

WebCodecs 硬件选项：Chrome 报告 `prefer-hardware` 支持；强制硬件实测 6.6–9.3s，默认 `no-preference` 6.6–7.8s，差异基本是波动。默认不强制。

成片：

- `out/sky-blue/2026-11-10_canvas-fast-30fps/video.mp4`
- `out/sky-blue/2026-11-10_canvas-fast-60fps/video.mp4`

## 最终建议

- Windows 当前最佳：**当前引擎 + 4 workers + JPEG 直通**，30s 约 21s。
- 不建议为速度迁移到 Remotion/Revideo/Editly/Motion Canvas。
- 下一步真正有潜力的方向：**WebCodecs + Mediabunny**（去掉截图回读），或**原生 Canvas/Skia**（重写画面）。
