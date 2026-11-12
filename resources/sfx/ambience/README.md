# 环境音效库（ambience）

给「人声 + 环境声」分层混音用。全部来自 **Mixkit**（https://mixkit.co/free-sound-effects/），
Mixkit Free License：可个人/商业使用、无需署名，但不能把音效本身作为独立素材再分发。

文件命名：`<类别>__<英文标题>.mp3`，方便按前缀筛。

| 文件 | 时长 | 适合 |
|---|---|---|
| `wind__wind-in-the-top-of-the-mountain.mp3` | 31.8s | 空旷高山、天地、序章 |
| `wind__wind-blowing-ambience.mp3` | 61.8s | 通用风声底 |
| `wind__breeze-through-the-trees.mp3` | 14.3s | 竹林、夜晚、山风 |
| `wind__scary-graveyard-wind.mp3` | 12.4s | 义庄、破屋、荒凉 |
| `rain__light-rain-loop.mp3` | 15.0s | 小雨、可循环 |
| `thunder__thunder-rumble-during-a-storm.mp3` | 51.8s | 远处闷雷、剑阵 |
| `bell__church-bell-calling.mp3` | 28.0s | 钟声、收尾 |
| `chimes__relaxing-bell-chime.mp3` | 1.7s | 单声铃、点缀 |
| `wind-chimes__wind-chimes.mp3` | 2.5s | 屋檐铜铃（尾声） |
| `birds__wild-raven-bird-calling.mp3` | 1.7s | 乌鸦（义庄） |
| `fire__campfire-crackles.mp3` | 24.0s | 火把、古洞 |
| `fire__campfire-burning-crackles.mp3` | 14.1s | 火堆、余烬 |
| `water-drop__water-drop-splashes-in-cave.mp3` | 2.0s | 冰室/洞穴滴水（间隔重复） |
| `crowd__restaurant-crowd-talking-ambience.mp3` | 120.0s | 人群底（慎用，偏餐厅） |

## 用在哪（《诛仙》八场）

| 场 | 建议铺底 |
|---|---|
| 1 序章 | 山顶风，低音量；或干脆留白 |
| 2 碧瑶 | 闷雷压低 + 山顶风 |
| 3 陆雪琪 | 竹林风 |
| 4 鬼王 | 洞穴滴水（每 3–6 秒一次）+ 极低的山顶风 |
| 5 道玄 | 闷雷 + 风声 |
| 6 玲珑 | 火把噼啪 + 滴水 |
| 7 田不易 | 义庄风 + 乌鸦（一两次） |
| 8 尾声 | 铜铃 + 微风 |

## 混音原则

- 人声保持 0 dB 基准，环境声压到 **−28 ~ −22 dB**，只做“底”，不抢字。
- 环境声单独一条轨，进出用 1–2 秒淡入淡出，不要硬切。
- 短音效（滴水、乌鸦、铃）按间隔重复，不要连续 loop，否则像机器。
- 需要循环用 `cine/audio/engines/bgm_loop.py`，不要用播放器自带的 loop。
