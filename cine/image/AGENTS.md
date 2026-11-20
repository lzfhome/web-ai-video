# cine/image

Ark 素材生成：Seedream（图）/ Seedance（视频）。

## 什么时候用

- 需要具体的场景图、插画、短片段，而不是代码能画出来的东西
- 当前没有 line 默认调用；需要时手动生成，再把文件接进 `film.js` / `film.canvas.js`

## 目录

| 位置 | 作用 |
|---|---|
| `lib/ark_client.py` | 配置、HTTP、任务轮询、下载 |
| `engines/ark.py` | CLI：dry-run、落盘、批量 assets、拆帧 |

## 配置

读 `tools/video-studio/config.json` + `config.secrets.json`，或用环境变量覆盖：

- `ARK_API_KEY`
- `ARK_BASE_URL`
- `VIDEO_STUDIO_DIR`

## 用法

```powershell
# 先看计划，不花钱（默认 dry-run）
python cine/image/engines/ark.py image --prompt "..." --out lessons/003/assets/img/a01.jpg
python cine/image/engines/ark.py video --prompt "..." --out lessons/003/assets/clips/v01.mp4

# 确认后才提交
python cine/image/engines/ark.py image ... --yes

# 批量：assets_ark.json 的 items[]，每条 kind=image/video
python cine/image/engines/ark.py assets lessons/003/assets_ark.json --yes
```

## 约定

- **默认 dry-run**，不加 `--yes` 不花钱
- 视频默认 `generate_audio=false`；要环境声加 `--generate-audio`
- 生成画面默认叠加「AI 示意图 / AI 生成画面」角标（由各产线负责）
- 文字、UI、排版一律代码生成，不要交给模型

## 注意

- 素材价格按火山方舟计费，批量前先看 dry-run 的计划
- 生成结果是普通文件，落在 `assets/`，和手放素材一样用
