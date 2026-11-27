# cine/

共享合成引擎。只放「怎么画、怎么响」，不放某条产线的业务逻辑，也不放原料。

```text
audio/    配乐、音效、旁白时间轴、混音
video/    成片：engines/dom（DOM+Three.js）、engines/canvas（WebCodecs）、engines/deliver.py
image/    Ark：Seedream 图 / Seedance 视频
media/    站外素材：B 站视频/音频/封面/字幕（yutto）
vendor/   第三方运行时（three.js）
```

一条产线 = `workspaces/vibe-knowledge/line/<name>/`，它选择这里的引擎并给参数。
产物 = `workspaces/vibe-knowledge/projects/<work>/`，不进 git。

各子目录的说明在各自的 `AGENTS.md`。

## 分层

每个域内部按四层放，引擎和零件不混：

```text
<domain>/
├── lib/       零件：WAV 读写、DSP、编码封装，被引擎 import
├── engines/   引擎：有明确入口，能单独跑，产出文件
├── clients/   客户端：第三方 API 的薄封装，被引擎和外部工具 import
└── tools/     工具：取素材、检查，不参与渲染
```

跨域零件放 `tools/lib/`（ffmpeg、browser、server、paths）。

`audio/`、`media/` 已按这个分层；`video/`、`image/` 逐步对齐。新增引擎时先决定落在哪一层，不要往 `tools/` 里塞。

## BGM 获取

详细命令和注意事项见 [`audio/AGENTS.md`](audio/AGENTS.md) 的「BGM 获取」一节。原则：

- 先找官方/CC 源：YouTube 作者的 Topic 频道、Free Music Archive、Pixabay、Mixkit、Freesound。
- 免费低音质兜底用网易云 `fee=8` 的 128kbps 版，仅自用；发布/商用要授权。
- 工具：`tools/local/yt-dlp/yt-dlp.exe` + `tools/local/ffmpeg/...`。
- 固化脚本：`python cine/audio/tools/get_bgm.py search|download|netease|adopt|library`，输出 JSON，agent 直接调用。
- 网易云专用：`musicdl` 已装在 `tools/local/musicdl`，封装 `python cine/audio/tools/musicdl_bgm.py search|download`，可下 FLAC + 320k MP3。
- 网络先直连；超时/重置时用 `socks5://127.0.0.1:1080`，或按 `AGENTS.md` 用用户提供的代理。
- BGM 文件放 `resources/music/`，不要放 `cine/`；`resources/` 的音频只留本地，更新本目录 `AGENTS.md` 的曲目表即可。

## B 站素材

参考视频用 [`media/`](media/AGENTS.md) 的 yutto 封装下载，不要直接调 yutto：

```powershell
python cine/media/engines/bilibili.py setup
python cine/media/engines/bilibili.py doctor
python cine/media/engines/bilibili.py download BV1BV4y1p7Xb
```

- 默认输出 `resources/references/bilibili/<BV>/`，含视频、`cover.jpg`、`meta.json`。
- 未登录只有 480P；要 1080P+ 先 `login` 扫码（凭证在 `tools/local/yutto-auth.toml`）。
- stdout 是 JSON，进度走 stderr；详细参数、质量表和失败处理见 `media/AGENTS.md`。
