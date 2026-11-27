# cine/media

站外素材获取。目前只有 B 站：视频 / 音频 / 封面 / 弹幕 / 字幕，落到 `resources/references/bilibili/`。

上游是 [`yutto`](https://github.com/yutto-dev/yutto)（GPL-3.0-only），源码 vendored 在 `repos/yutto/`，运行时装在 `tools/local/venv-yutto/`。本目录只通过子进程调用它的 CLI，不 import。

## 目录

| 位置 | 作用 |
|---|---|
| `engines/bilibili.py` | 唯一入口：`info` / `download` / `login` / `status` / `setup` / `doctor` |
| `clients/yutto.py` | 定位 venv / ffmpeg / 登录态，拼参数、跑进程 |

## 安装

只装到 D 盘项目内，不写 C 盘：

```powershell
python cine/media/engines/bilibili.py setup
python cine/media/engines/bilibili.py doctor
```

- `setup` 建 `tools/local/venv-yutto`，安装固定版本 `yutto==2.3.1`（`clients/yutto.py` 的 `YUTTO_VERSION`）。
- `tools/local/` 已被 git 忽略；新克隆的仓库必须跑一次 `setup`。
- ffmpeg 自动找 `tools/local/ffmpeg/*/bin/ffmpeg.exe`，也可用 `FFMPEG` 环境变量。
- `doctor` 输出 JSON：`yutto` / `ffmpeg` / `ffprobe` / 登录态。

## 登录（1080P 及以上必须）

未登录时 B 站只给到 480P。登录凭证写到项目内 `tools/local/yutto-auth.toml`（不写用户目录）：

```powershell
# 弹出二维码图片，手机 B 站扫码；默认等 180 秒
python cine/media/engines/bilibili.py login

# 纯终端二维码（无桌面环境）
python cine/media/engines/bilibili.py login --mode terminal

python cine/media/engines/bilibili.py status
```

也可以临时用 SESSDATA（浏览器 Cookie 里的值）：

```powershell
$env:BILIBILI_SESSDATA = "..."
# 或
python cine/media/engines/bilibili.py download BV... --sessdata "..."
```

## 下载

```powershell
# 看元数据（标题/UP/时长/分P/封面 URL）
python cine/media/engines/bilibili.py info BV1BV4y1p7Xb

# 默认最高可用清晰度，输出 resources/references/bilibili/<BV>/
python cine/media/engines/bilibili.py download https://www.bilibili.com/video/BV1BV4y1p7Xb/

# 指定 1080P、指定目录
python cine/media/engines/bilibili.py download BV1BV4y1p7Xb -q 80 `
  --out resources/references/bilibili/BV1BV4y1p7Xb

# 只要音频（m4a）
python cine/media/engines/bilibili.py download BV1BV4y1p7Xb --audio-only

# 连弹幕/字幕一起存（字幕需要登录）
python cine/media/engines/bilibili.py download BV... --danmaku --subtitle

# 先看会执行什么
python cine/media/engines/bilibili.py download BV... --dry-run
```

- 支持完整 URL、`BV1xxxxxxxxx`、`av123456`、`b23.tv` 短链、分 P URL。
- `--quality`：`127` 8K / `126` Dolby Vision / `125` 4K HDR / `120` 4K / `116` 1080P60 / `112` 1080P+ / `100` 智能修复 / `80` 1080P / `74` 720P60 / `64` 720P / `32` 480P / `16` 360P。不传就是最高可用。
- 默认不存弹幕和字幕，输出目录会干净一些；需要再加 `--danmaku` / `--subtitle`。
- 已存在文件时 yutto 会跳过；要重下加 `--force`。
- 网络不通时加 `--proxy http://172.16.11.83:1087`；直连优先。

## 产物契约

```text
resources/references/bilibili/<BV>/
├── <标题>.mp4        # 或 .m4a / .flac；多 P 时可能在子目录
├── cover.jpg         # 封面
├── meta.json         # 来源、UP、时长、清晰度、文件列表、ffprobe 结果
└── *.ass / *.xml     # 可选：字幕 / 弹幕
```

`meta.json` 由本工具写，字段：

- `source`：`url` + B 站 API 的 `bvid/aid/cid/title/owner/duration/pubdate/pic/desc/pages/stat`
- `download`：`at/quality/quality_name/audio_only/auth/yutto/elapsed_s`
- `files`：每个媒体文件的 `path/name/size/duration/width/height/vcodec/fps/acodec`
- `cover`：封面路径

stdout 永远是一段 JSON（`ok` 为 `true/false`），进度和中文日志走 stderr；agent 直接解析 stdout。

## smoke test

```powershell
python cine/media/engines/bilibili.py doctor
python cine/media/engines/bilibili.py info BV1BV4y1p7Xb
python cine/media/engines/bilibili.py download BV1BV4y1p7Xb --dry-run
```

三条都返回 `"ok": true` 即通过；第一条不需要网络。真正的下载测试用短分 P 或 `--audio-only`，避免拉大文件。

## 失败怎么处理

| 现象 | 处理 |
|---|---|
| `没有安装 yutto` | 跑 `setup` |
| 只有 480P / 提示未登录 | 跑 `login`，或设 `BILIBILI_SESSDATA` |
| `yutto 退出码 != 0` | 看 JSON 里的 `log`；常见是登录失效、需要大会员、番剧地区限制 |
| 找不到媒体文件 | 看 `out` 目录；yutto 可能因合并失败留下 `.frag`/临时文件，重跑加 `--force` |
| 网络超时/重置 | 加 `--proxy`，或换网络重试 |

## 上游与许可

- 上游：`https://github.com/yutto-dev/yutto`，vendored commit、License 见 `repos/SOURCES.md`。
- yutto 是 GPL-3.0-only；本项目把它当独立可执行程序调用，源码保留在 `repos/yutto/`。
- 下载内容版权归原 UP 主/版权方；只作自用参考，不发布、不商用。
