# vibe-knowledge 车间

Vibe 知识短片的生产线：cine 引擎 + 模板 + 工具 + 音色。**不放具体作品**；作品在 `projects/<work>/`。

## 内容

```text
workspaces/vibe-knowledge/
├── cine/                 # 渲染引擎（项目里用软链引用）
├── templates/
│   ├── lesson/           # 空白作品模板
│   ├── series.json       # 系列配置模板
│   ├── BRIEF.md
│   ├── examples-briefs/
│   ├── examples-lessons/
│   └── publish/
├── tools/
│   ├── new_project.py    # 新建作品
│   ├── edge_tts_timings.py
│   ├── silent_timings.py
│   ├── check_timings.py
│   └── update_series.py
└── voice/host-ref.wav
```

## 新建作品

```bash
python3 workspaces/vibe-knowledge/tools/new_project.py my-film --title "我的片子"
```

## 渲染

```bash
CINE_ROOT=projects/my-film python3 workspaces/vibe-knowledge/cine/tools/record.py my-film --fps 30
CINE_ROOT=projects/my-film python3 workspaces/vibe-knowledge/cine/tools/finish.py my-film --fps 30
```

`CINE_ROOT` 指向项目根；`record.py` / `finish.py` 从项目根的 `lessons/<lesson>/` 找源码，`build` 软链到 `out/_tmp/<work>/build`。

## 模板

- `templates/lesson/film.js`：来自 skill 的 `film.skeleton.js`
- `templates/lesson/narration.json`：母版 A 旁白骨架
- `templates/lesson/facts.md`：事实清单模板
- `templates/lesson/assets/img/`：作品图片目录

## 共享引擎

`projects/<work>/cine` 软链到本车间的 `cine/`。改引擎只改这里，所有作品同步生效。
