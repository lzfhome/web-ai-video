---
name: session-log
description: Use at the start and end of every AI conversation/session to record session details into a log. Also use when the user asks to 记录会话, 保存会话, session log, or "记录一下这次会话".
---

# Session Log

Record every opencode conversation session into a local log so past work can be reviewed and referenced later. Trigger at the **start** and **end** of each session.

## Where to write

- Log directory: `~/.config/opencode/session-logs/`
- **One file per session, named by session ID**: `~/.config/opencode/session-logs/<session-id>.md` (e.g. `ses_f4c6dfabdffepf7QaMHJDhkI80.md`).
- Never rewrite or delete an existing file. Update the same file at session end.
- Use the `bash` tool to check whether the file exists, then append with a heredoc or `mkdir -p` + append. Create the directory if missing.

## Getting the current session ID

Find the session ID by querying the opencode SQLite database, matching the newest session for the current directory:

```bash
sqlite3 ~/.local/share/opencode/opencode.db \
  "SELECT id FROM session WHERE directory='<当前目录>' ORDER BY time_updated DESC LIMIT 1;"
```

The result is an ID like `ses_f4c6dfabdffepf7QaMHJDhkI80`.

If `sqlite3` is unavailable or the DB cannot be read, ask the user for the session ID, or fall back to `YYYY-MM-DD-HHMM.md`.

## When to log

**At session start** (first user message of a session), create the `<session-id>.md` file with the fields known at that point. Mark it as "in progress".

**At session end** (conversation is wrapping up, user says goodbye, or a natural pause), append the final fields to the same file.

## Entry format

```markdown
# 会话 <session-id>

- **时间**: 2026-09-18 14:30 ~ 15:05
- **项目/目录**: /home/oliver/workspace/AIWork
- **模型**: opencode-go/deepseek-v4-flash
- **用户目标**: 一句话概括用户本次想做什么
- **主要动作**: 关键步骤列表（阅读了哪些文件、改了哪些文件、跑了哪些命令）
- **关键决策**: 用户确认过的技术选型或方向
- **修改的文件**: `path/to/file`（如适用）
- **遇到的问题**: 报错、阻碍及如何解决（如适用）
- **结果**: 最终成果 / 待办事项 / 下一步建议
```

Fill in the fields with actual data from the session. If a field has no data yet (e.g. result), write `待补充` at session start and fill it in at session end.

## Rules

- Keep entries concise; this is a review log, not a transcript.
- Use the session's real dates, paths, model, and command outputs — do not fabricate.
- Do not log secrets, API keys, or credentials.