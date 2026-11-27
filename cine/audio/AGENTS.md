# cine/audio

配乐、音效、旁白时间轴、混音。

## 目录

| 位置 | 作用 |
|---|---|
| `engines/bed.py` | 按 `lesson.json` 生成 `bed.wav`（垫乐）+ `sfx.wav`（点音效） |
| `engines/score.py` | 展示片的整首配乐（合成器，无采样） |
| `engines/bgm_loop.py` | 把一首 BGM 无缝循环到指定长度 |
| `engines/tts_silent.py` | 无旁白：只生成 `timings.json` + 静音 `narration.wav` |
| `engines/tts_edge.py` | edge-tts 配音 + 逐字近似对齐 |
| `engines/tts_doubao.py` | 豆包 Seed-TTS 2.0 配音 + 同一套对齐 |
| `engines/mix.py` | 四条轨相加 + 响度归一 + 限幅 |
| `lib/wavio.py` | WAV 读写、重采样、补齐 |
| `lib/dsp.py` | 旁白包络、ducking、限幅 |
| `clients/doubao_tts.py` | 豆包语音客户端（`synth()` / CLI），产线和 video-studio 共用 |
| `tools/get_bgm.py` | BGM 搜索/下载/网易云兜底/sidecar/索引（agent 用，输出 JSON） |
| `tools/musicdl_bgm.py` | 网易云专用：musicdl 搜索、FLAC 下载、转 320k MP3（agent 用） |
| `tools/check_timings.py` | 检查时间轴有没有「句子挤在一起」 |
| `tools/bgm_lead.py` | 通用：任意音频测开头静音，输出源曲裁剪起点；poetry 映射为 `bgm_from`（裁到 1.2s） |

**分层**：`lib/` 是零件，`engines/` 是可执行引擎，`clients/` 是被 import 的客户端，`tools/` 是取素材/检查的工具。

## 谁在用

- `line/dom-narrated/render.py`：`engines/tts_silent.py` / `engines/tts_doubao.py` / `engines/tts_edge.py`
- `line/dom-narrated/finish.py`：`engines/bed.py` + `engines/mix.py`
- `line/poetry/render.py`：`engines/tts_silent.py`，再交给 dom-narrated
- `line/poetry-tts/render.py`：`clients/doubao_tts.py` + `engines/tts_silent.py` 的 timings

## 约定

- 所有 WAV：48 kHz、立体声、16-bit，长度 = `round(duration * 48000)`
- 旁白永远在 0 dB，垫乐自动压低（duck）
- 自定义 BGM 在 `film.js` 的 `music` 数组里声明；`bgm: true` + `user_request` 会让 `bgm_force.py` 保留它

## BGM 获取

BGM 文件统一放 `resources/music/`，不要放 `cine/`。获取顺序：

1. **官方/CC 优先**：YouTube 作者的 Topic 频道、Free Music Archive、Pixabay、Mixkit、Freesound。
2. **免费低音质兜底**：网易云 `fee=8` 的 128kbps 版本，仅自用；发布/商用要授权。
3. 第三方聚合站/爬虫只作最后手段，平台 ToS 和版权风险自担。

### 固化脚本（Agent 用）

脚本：`cine/audio/tools/get_bgm.py`。所有子命令输出 JSON（成功 `ok: true`，失败 `ok: false`），agent 直接解析即可。

```powershell
# 搜索候选
python cine/audio/tools/get_bgm.py search "花火が瞬く夜に 羽肿" --limit 5 --proxy socks5://127.0.0.1:1080

# 从 YouTube 下载并转 MP3
python cine/audio/tools/get_bgm.py download "https://www.youtube.com/watch?v=<id>" `
  --name hanabi_yuzhong --proxy socks5://127.0.0.1:1080

# 网易云 fee=8 免费低音质版
python cine/audio/tools/get_bgm.py netease <song_id> --name hanabi_yuzhong_128

# 给已有音频补 sidecar
python cine/audio/tools/get_bgm.py adopt "resources/music/<file>.mp3" `
  --name <name> --title "..." --artist "..." --source youtube --source-url "..."

# 汇总所有 sidecar
python cine/audio/tools/get_bgm.py library
```

- `search` 结果受地区影响，优先选 `is_topic: true` 且时长匹配的候选；不对就换关键词或直接给 URL。
- `download` 会自动找 `tools/local` 或 PATH 里的 `yt-dlp` / `ffmpeg`；找不到再设 `YT_DLP` / `FFMPEG`。
- `download` / `netease` 写入 `resources/music/<name>.mp3` 和 `<name>.json` sidecar。
- `adopt` 给已有音频补 sidecar；`library` 汇总成 `resources/music/library.json`。
- 如果 `python` 指向 Windows Store 别名（运行无输出/9009），用真实解释器路径：`C:\Users\Oliver\AppData\Local\Programs\Python\Python312\python.exe`，或把该目录加入 PATH。

### 网易云 musicdl（已装在本项目）

`musicdl` 已装到 `D:\AIWork\tools\local\musicdl`（`pip --target`，没动 C 盘）。封装脚本：`cine/audio/tools/musicdl_bgm.py`。

```powershell
# 搜索网易云
python cine/audio/tools/musicdl_bgm.py search "花火が瞬く夜に 羽肿"

# 按 song id 下载：默认 FLAC → 320k MP3，并保留 FLAC
python cine/audio/tools/musicdl_bgm.py download `
  --query "花火が瞬く夜に 羽肿" --id 434902428 `
  --name hanabi_yuzhong --keep-flac
```

- `search` 返回 `id / name / singers / album / ext / size / url`；下载用 `--id` 精确匹配。
- 默认输出 `resources/music/<name>.mp3`（320 kbps）+ `<name>.flac` + `<name>.json`。
- 搜索结果里的 `duration` 有时是 5 秒（接口 bug），以 `ffprobe` 实际时长为准。
- `musicdl` 许可证是 **PolyForm Noncommercial 1.0.0**，仅个人/非商业使用。
- 第三方解析接口会失效；失败就换 `get_bgm.py netease` 或 YouTube 源。

### 工具与网络

- `yt-dlp`：`D:\AIWork\tools\local\yt-dlp\yt-dlp.exe`
- `ffmpeg`：`D:\AIWork\tools\local\ffmpeg\ffmpeg-9.0.2-essentials_build\bin`
- 先直连；超时/重置时用本机 SOCKS5 `socks5://127.0.0.1:1080`。用户提供的 `http://172.16.11.83:1087` 只在能转发时用。

### 搜索

```powershell
$yt = 'D:\AIWork\tools\local\yt-dlp\yt-dlp.exe'
& $yt --proxy socks5://127.0.0.1:1080 --flat-playlist `
  --print "%(id)s`t%(duration)s`t%(title)s`t%(channel)s" `
  "ytsearch5:花火が瞬く夜に 羽肿"
```

优先选频道名带 `- Topic` 的官方音频；核对时长和原曲一致。翻奏、剪辑版通常时长不同。

### 下载并转 MP3

```powershell
$ff = 'D:\AIWork\tools\local\ffmpeg\ffmpeg-9.0.2-essentials_build\bin'
& $yt --proxy socks5://127.0.0.1:1080 --no-playlist --ffmpeg-location $ff `
  -f bestaudio -x --audio-format mp3 --audio-quality 0 --embed-metadata `
  -o "D:\AIWork\resources\music\%(id)s.%(ext)s" `
  "https://www.youtube.com/watch?v=<id>"
```

- 必须给 `--ffmpeg-location`，否则会报 `ffprobe and ffmpeg not found`。
- YouTube 源通常是 Opus/WebM；转 MP3 后约 210–250 kbps，属于转码，不是无损。
- 下载后先 `ffprobe` 核对时长/码率，再改成 `<mood>_<artist>.mp3` 这种 ASCII 文件名；中文标题写进 `resources/music/AGENTS.md`。

### 网易云免费版兜底

```powershell
Invoke-WebRequest "https://music.163.com/song/media/outer/url?id=<id>.mp3" `
  -OutFile "D:\AIWork\resources\music\_incoming\<name>.mp3" -UseBasicParsing
```

- 只对 `fee=8` 的免费低音质曲有效；VIP/版权曲会失败或返回错误页。
- 这是 128kbps 试听版，仅自用；发布/商用要授权。

### 入库与混音（本地素材库）

- 临时下载放 `resources/music/_incoming/`，确认后移到 `resources/music/`。
- 更新 `resources/music/AGENTS.md`：原曲、作者、时长、码率、来源、许可/用途。
- 进 `finish.py` 混音前，可转成统一 WAV：

```powershell
ffmpeg -i in.mp3 -ar 48000 -ac 2 -c:a pcm_s16le out.wav
```

### 已用过的源

- YouTube Topic：饭碗的彼岸、羽肿、MoreanP（官方音频）。
- 网易云：`1341912654` / `434902428` / `1426611455` / `506650377`。
- FMA CC BY：Jelsonic、Matthew C. Wright、Purrple Cat（备选，需署名）。

> 版权：YouTube/网易云的曲目归原作者；`resources/music/AGENTS.md` 里写清“自用/不发布”，发布前换授权版本。

## 注意

- `score.py` 是展示片的完整配乐，日常短片用不到；短片走 `bed.py` + `music`
- 没有 ffmpeg 时混音会失败，先跑 `python tools/doctor.py`

## 豆包语音（Seed-TTS 2.0）

`clients/doubao_tts.py` 走 `https://openspeech.bytedance.com/api/v3/tts/unidirectional`，
鉴权是 `X-Api-Key`，**和方舟的 `ark-` key 不通用**，要豆包语音控制台那份 UUID 形态的 key。

key 的查找顺序：函数参数 → `DOUBAO_TTS_API_KEY` / `TTS_API_KEY` 环境变量 →
`~/.config/aiwork/tts.env` → `tools/video-studio/config.secrets.json` 的 `tts_api_key`。
最后一条是为了和视频工作台共用同一把 key。

```bash
python cine/audio/clients/doubao_tts.py --list
python cine/audio/clients/doubao_tts.py --text "天地不仁，以万物为刍狗。" \
  --voice zh_male_qingcang_uranus_bigtts --speed 0.92 --out a.mp3
```

产线里把 `narration.json` 的 voice 写成：

```json
{"engine": "doubao", "voice": "zh_male_qingcang_uranus_bigtts", "speed": 0.92}
```

然后 `python project.py render <项目> --line dom-narrated --tts doubao`。
