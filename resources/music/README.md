# 共享 BGM

## 当前曲目

| 文件 | 原曲 | 作者 | 时长 | MP3 | FLAC |
|---|---|---|---:|---|---|
| `rainy-blue_fanwan.mp3` / `.flac` | Rainy Blue (蓝色阴雨) | 饭碗的彼岸 / 夜莺与玫瑰 | 4:27 | 320 kbps | ✅ |
| `hanabi_yuzhong.mp3` / `.flac` | 花火が瞬く夜に | 羽肿 | 4:31 | 320 kbps | ✅ |
| `dust-fireflies_yijiu.mp3` / `.flac` | 尘埃与流萤 | 依旧在雨中等你 / 鹤见江野 | 4:33 | 320 kbps | ✅ |
| `summer-nostalgia_moreanp.mp3` / `.flac` | 忆夏思乡 | MoreanP | 4:23 | 320 kbps | ✅ |

- 来源：网易云，通过 `musicdl` 的 `NeteaseMusicClient` 获取。
- MP3 是 FLAC 转的 320 kbps / 48 kHz；FLAC 原文件保留。
- 每首旁边有同名 `.json` sidecar；`library.json` 是汇总索引。
- 用途：自用成片。版权归原作者。

## 获取方式（Agent）

```powershell
# 搜索
python cine/audio/tools/musicdl_bgm.py search "花火が瞬く夜に 羽肿"

# 按 song id 下载，默认转 320k MP3，并保留 FLAC
python cine/audio/tools/musicdl_bgm.py download `
  --query "花火が瞬く夜に 羽肿" --id 434902428 `
  --name hanabi_yuzhong --keep-flac

# 重新汇总索引
python cine/audio/tools/get_bgm.py library
```

`musicdl` 安装在 `D:\AIWork\tools\local\musicdl`，没有动 C 盘。

## 备注

- `musicdl` 走的是第三方解析接口，URL 会过期；每次下载前重新搜索。
- 它的许可证是 **PolyForm Noncommercial 1.0.0**：仅个人/非商业使用。
- `search` 返回的 `duration` 有时是 5 秒（接口 bug），以下载后 `ffprobe` 的时长为准。
