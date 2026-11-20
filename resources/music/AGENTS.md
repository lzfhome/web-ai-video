# 共享 BGM

## 当前曲目

| 文件 | 原曲 | 作者 | 时长 | 情绪/用途 | MP3 | FLAC |
|---|---|---|---:|---|---|---|
| `rainy-blue_fanwan.mp3` / `.flac` | Rainy Blue (蓝色阴雨) | 饭碗的彼岸 / 夜莺与玫瑰 | 4:27 | 温柔 / 回忆 | 320 kbps | ✅ |
| `hanabi_yuzhong.mp3` / `.flac` | 花火が瞬く夜に | 羽肿 | 4:31 | 温柔 / 夏夜 | 320 kbps | ✅ |
| `dust-fireflies_yijiu.mp3` / `.flac` | 尘埃与流萤 | 依旧在雨中等你 / 鹤见江野 | 4:33 | 安静 / 回忆 | 320 kbps | ✅ |
| `summer-nostalgia_moreanp.mp3` / `.flac` | 忆夏思乡 | MoreanP | 4:23 | 温柔 / 乡愁 | 320 kbps | ✅ |
| `zichuan_mingxin.mp3` | 紫川·铭心 | 陈雪燃 | 2:13 | 紫川 / 克制悲怆 | 320 kbps | — |
| `zichuan_mingji.mp3` | 紫川·铭记 | 陈雪燃 | 3:15 | 紫川 / 史诗回忆 | 320 kbps | — |
| `zichuan_axiu.mp3` | 阿秀 | 陈雪燃 | 3:36 | 紫川 / 人物主题 | 320 kbps | — |
| `zichuan_geying.mp3` | 紫川·歌舞升平 | 陈雪燃 | 2:32 | 紫川 / 明亮朝堂 | 320 kbps | — |
| `sanguo_hero_dawn.mp3` | 英雄的黎明 | 横山菁儿 | 3:36 | 三国 / 苍凉史诗 | 320 kbps | — |
| `qijian_warsong.mp3` | 七剑战歌 | 川井宪次 | 6:05 | 武侠 / 大战 | 320 kbps | — |
| `langya_beizhuang.mp3` | 悲壮 | 孟可 / 吕亮 | 2:55 | 权谋 / 悲壮 | 320 kbps | — |
| `gudai_war_desolate.mp3` | 古代战争荒凉沧桑配乐 | 猴子音悦 | 2:14 | 古代战争 / 荒凉 | 320 kbps | — |
| `gobi_beacon.mp3` | 戈壁烽火 (古代战争) | 海明 MING | 2:56 | 边塞 / 烽火 | 320 kbps | — |
| `changan_12.mp3` | 長安十二時辰 | 村松崇継 | 2:41 | 长安 / 紧张权谋 | 320 kbps | — |
| `datang_glory.mp3` | 荣耀梦幻版 | 小里多 | 3:37 | 大唐 / 盛世抒情 | 320 kbps | — |
| `kangxi_war.mp3` | 康熙王朝大战 | 倪轮月 | 1:20 | 大战 / 短，需 loop | 320 kbps | — |
| `damgong_tea.mp3` | 一曲茶炉暖色 | 林海 | 2:13 | 宫廷 / 安静 | 320 kbps | — |
| `qin_empire.mp3` | 大秦帝国 | 吴欣叡 | 1:25 | 大秦 / 雄壮，短，需 loop | 320 kbps | — |

- 来源：网易云，通过 `musicdl` 的 `NeteaseMusicClient` 获取。
- 早期 4 首保留 FLAC；新增曲目默认只保留 320 kbps / 48 kHz MP3（需要无损时下载加 `--keep-flac`）。
- 当前 18 首里，17 首是纯音乐；`dust-fireflies_yijiu.mp3` 是人声曲。
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
