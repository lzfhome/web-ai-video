# 15 · 本地增强层：Seedance / Seedream（火山方舟）

不装 Renoise 时，用本机 `video-studio` 的火山方舟配置生成**写实/水墨关键图**和**动态镜头**。代码做字卡、数据、转场；Seedance/Seedream 只补代码做不好的 1–3 个镜头。

## 配置

默认读取：

```
/home/oliver/workspace/AIWork/tools/video-studio/config.secrets.json
/home/oliver/workspace/AIWork/tools/video-studio/config.json
```

- 密钥只放 `config.secrets.json`（或环境变量 `ARK_API_KEY` / `ARK_BASE_URL`），**不要写进项目**。
- 换目录：`export VIDEO_STUDIO_DIR=/path/to/video-studio`
- 跑工具建议用 `CINE_PY`（`--frames` 需要 numpy）：
  `CINE_PY=~/.venvs/cine/bin/python`

## 模型

| 用途 | 模型 | 说明 |
|---|---|---|
| 图片（便宜） | `doubao-seedream-5-0-260128` | Seedream 5.0 lite，2K/4K，适合场景、氛围、静帧 |
| 图片（最强） | `doubao-seedream-5-0-pro-260628` | 细节更好，贵一些 |
| 视频（测试/性价比） | `doubao-seedance-2-0-mini-260615` | 480p/720p，4–15s，适合试镜头 |
| 视频（快速） | `doubao-seedance-2-0-fast-260128` | 480p/720p，首尾帧/参考图 |
| 视频（专业） | `doubao-seedance-2-0-260128` | 最高 4K，参考视频/音频、延长 |
| 视频（长叙事） | `doubao-seedance-2-5-260628` | 最高 1080p、30s/段 |

视频默认 `generate_audio=false`，不生成人声/音效；需要环境声时加 `--generate-audio`。

## 先看计划，再提交（Skill 硬规矩）

工具默认 **dry-run**，只打印模型、参数、输出路径，不花钱。用户在对话里明确同意后，再加 `--yes`。

```bash
# 1. 看计划（不提交）
python3 skills/vibe-knowledge/tools/ark_media.py image \
  --prompt "ink wash tiger in moonlight, sepia monochrome, 1920s silent film, high contrast, grain, no text, no watermark" \
  --out lessons/003/assets/img/a01.jpg

# 2. 确认后生成
python3 skills/vibe-knowledge/tools/ark_media.py image ... --yes

# 3. 视频：用已生成的图做首帧，4 秒 480p 试镜头
python3 skills/vibe-knowledge/tools/ark_media.py video \
  --prompt "the tiger breathes slowly, mist drifts, slow push-in" \
  --first-frame lessons/003/assets/img/a01.jpg \
  --duration 4 --resolution 480p \
  --out lessons/003/assets/clips/v01.mp4 --frames --yes
```

`--frames` 会自动调用 `clip2frames.py`，输出 `lessons/003/assets/clips/v01/0001.jpg…` 和 `info.json`，打印 `n`；`film.js` 里用 `vclip({dir:A("clips/v01"), n})`。

## 批量：assets_ark.json

```json
{
  "items": [
    {
      "id": "a01",
      "kind": "image",
      "model": "doubao-seedream-5-0-260128",
      "prompt": "ink wash tiger in moonlight, sepia, silent film, no text",
      "size": "2K",
      "out": "assets/img/a01.jpg"
    },
    {
      "id": "v01",
      "kind": "video",
      "model": "doubao-seedance-2-0-mini-260615",
      "prompt": "tiger breathes, mist drifts, slow push-in",
      "first_frame": "assets/img/a01.jpg",
      "resolution": "720p",
      "ratio": "16:9",
      "duration": 5,
      "out": "assets/clips/v01.mp4",
      "frames": true
    }
  ]
}
```

```bash
# 先全部 dry-run
python3 skills/vibe-knowledge/tools/ark_media.py assets lessons/003/assets_ark.json
# 用户确认后
python3 skills/vibe-knowledge/tools/ark_media.py assets lessons/003/assets_ark.json --yes
```

相对路径以 `assets_ark.json` 所在目录为基准。

## film.js 接法

```js
import { plate, vclip } from "../../cine/engine/know.js";

// 静帧：plate 自带推拉 + 暗角 +「AI 示意图」角标
const p = plate(s, { src: A("img/a01.jpg") });
p.update(t, t0, t1, { from: [1.04, 0, 0], to: [1.12, -30, 0] });

// 视频：clip2frames 拆好的帧
const v = vclip(s, { dir: A("clips/v01"), n: 150 });
v.update(t, t0, t1, { rate: 1, loop: false });
```

两档通用：`ENH` 开关控制 `plate/vclip` ↔ 代码 `layers`。

## 提示词

统一前缀（水墨/默片）：

```
Japanese ink wash, sepia monochrome, 1920s silent film, high contrast, film grain, soft vignette, no text, no letters, no watermark
```

- **人物**：写剪影 / 背影 / 远景 / 手部，不写具体脸；历史人物标「造型示意」。
- **动物**：侧影、动作、环境（月光、雾、草），不要求正脸特写。
- **构图**：给字卡留位置，写 `negative space on the left/right`。
- **视频**：只写变化 + 一个镜头运动（`slow push-in / dolly left`），4–8 秒；不要对白。
- **不要**让模型写字、数字、logo；文字全部由代码叠加。

## 安全与成本

- 不生成在世真人的脸、不模仿品牌 logo；生成画面在 `plate/vclip` 默认带「AI 示意图 / AI 生成画面」角标。
- Ark 按实际用量计费；先 dry-run 列参数，用户确认后再 `--yes`。测试用 480p/720p、4–5 秒；定稿再上 1080p/更高。
- 生成 URL 会过期，工具已自动下载到本地。
- `generate_audio=false` 默认关闭；知识大赏的 BGM 仍由 `finish.py` 的 `bgm_force` 强制处理。
