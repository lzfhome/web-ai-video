# Upstream Sources

这些是 vendored 参考源码（已移除各自 `.git`，内容在本仓库）。更新时按 URL 重新拉取，并更新 commit。

| 目录 | 上游 | Commit | License |
|---|---|---|---|
| `vibe-knowledge-andy/` | https://github.com/andyhuo520/vibe-knowledge | `c3a13a8` | MIT |
| `vibe-knowledge-worlds3/` | https://github.com/worlds3/vibe-knowledge | `0d0249f` | 仓库未声明 License（仅参考，不直接复用代码） |
| `vibe-knowledge-interactive/` | https://github.com/wchhywizd/vibe-knowledge-interactive | `240ec57` | 代码 MIT / 文档 CC BY 4.0 |

## 说明

- 上游仓库里的大媒体（mp4/mov/wav/m4a/gif）已由根 `.gitignore` 忽略；源码和文档保留。
- `resources/references/` 里的参考视频也默认忽略；需要版本化请用 Git LFS。
- 修改上游代码前，先在 `repos/SOURCES.md` 记录原因和 commit。
- 不把上游仓库的 `.git` 再嵌套进来；需要追踪上游时改用 submodule，并同步更新本文件。
