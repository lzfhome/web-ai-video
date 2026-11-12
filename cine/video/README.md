# cine/video

成片层：`engines/` 放渲染和交付引擎，`tools/` 放系列索引等工具。

## 文件

| 文件 | 作用 |
|---|---|
| `engines/dom/` | DOM/CSS + Three.js 渲染引擎（`index.html` + `core.js` + `record.py`） |
| `engines/canvas/` | Canvas + WebCodecs 快速通道（`index.html` + `engine.js` + `components.js`） |
| `engines/deliver.py` | 把 `build/lesson<lesson>.mp4` 收进 `deliveries/<日期>_<版本>/`，生成 cover / post / notes |
| `engines/queue.py` | 按 `queue.txt` 批量渲染 + 交付 |
| `tools/update_series.py` | 扫描项目，更新 `series.json`（集数、封面、时长），给课程页用 |

## deliver.py

```powershell
python cine/video/engines/deliver.py <lesson> --title "片名" --poster 12
python cine/video/engines/deliver.py <lesson> --out deliveries/2026-11-10_v1
```

- 默认直接 copy 视频流，不二次压缩
- 要压缩加 `--reencode`，要网页版加 `--web`
- `--poster` 是取封面的秒数

产物：

```text
deliveries/<日期>_<版本>/
├── video.mp4
├── cover.jpg
├── post.txt
└── notes.md
```

## queue.py

项目根放 `queue.txt`，每行 `课号|标题|封面秒`：

```powershell
python cine/video/engines/queue.py <work> --workers 2
```

## 注意

- 交付目录由 `deliver.py` 自己取名，不要手建
- `deliver.py` 只读 `build/`，不改 `build/`
