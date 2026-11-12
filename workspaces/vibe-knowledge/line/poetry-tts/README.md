# poetry-tts

`poetry` 的配音版：书封做背景、诗句由代码排版，**加一条真配音轨**。

和 `poetry` 的差别只有一处：场景时长不再写死，而是

```
本场秒数 = say.pre（画面先出）+ say.lead（停顿）+ 配音长度 + say.post（读完留白）
```

文字出现的时刻也跟着配音走：第一行在声音开口时出，后面每一行按配音长度均匀排开。

## 输入

只有一份：`line/poetry-tts/build.json`（支持 `//` 注释）。

```bash
python project.py build poetry-tts
```

会自动建项目（重名加 `-v2`）、复制封面和 BGM、配音、渲染、交付。

## 新增的字段

| 字段 | 默认 | 说明 |
|---|---|---|
| `voice` | `{"engine":"doubao","voice":"zh_male_qingcang_uranus_bigtts","speed":0.9}` | 配音音色，见 `python cine/audio/clients/doubao_tts.py --list` |
| `say.pre` | `0.6` | 画面先出多久再开口 |
| `say.lead` | `0.5` | 开口前的停顿 |
| `say.post` | `1.4` | 读完留白 |
| `scenes[].say` | 自动 | 这一场要读的文字；不写就是 `lines` 拼起来 |
| `scenes[].voice` | 顶层 `voice` | 单场换音色 / 语速，做多角色配音就靠它 |

### 多角色配音

```json
{ "voice": { "voice": "zh_female_gufengshaoyu_uranus_bigtts", "speed": 0.96 } }
```

按「谁在说话」选，不要按「画面里是谁」选：
旁白（包括描述某人心理的句子）用解说音色，直接引语才用角色本音。
年龄、性别、语气都要对上，否则一听就假。

其余字段（`cover` `lines` `palette` `type` `effects` `book` `bgm` `credit` `source` `header` `footer`）和 `poetry` 完全一样，见 `line/poetry/README.md`。

## 时长与节奏

- 每场时长由配音决定，`story` 里不用再写 `scene_seconds`。
- 想整体慢一点：`voice.speed` 调到 `0.85`，或加大 `say.lead` / `say.post`。
- 多行诗句的行间距（出场间隔）按配音长度自动算，范围 0.45–1.9 秒；想固定就写 `scenes[].gap.line_step`。
- 配音缓存存在 `build/audio/scXX.json`，文字/音色/语速没变就不重复合成；要强制重配加 `--force`。

## 成本

豆包语音按字符计费。八场、每场 10–25 字，整片约 150–200 字，成本可以忽略；
但改文案后重跑只重新合成改动过的场次。

## 重新渲染

```bash
python project.py render <项目> --line poetry-tts --workers 2
```

只改画面（不改文案）时加 `--from/--to` 可以只渲一段预览。

## 换一本小说

和 `poetry` 一样，只改 `build.json`：

1. `id` / `title`
2. `scenes[].cover`：封面图，放 `line/poetry-tts/assets/` 或任意相对路径
3. `scenes[].lines`：原文诗句（多行就写数组）
4. `scenes[].credit` / `source` / `header` / `footer`
5. `voice.voice`：换个音色
6. `bgm.src`

不需要改 `render.py`、`film.skeleton.js` 或引擎代码。
