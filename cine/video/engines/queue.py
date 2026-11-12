#!/usr/bin/env python3
"""串行渲染队列：读 <CINE_ROOT>/queue.txt，逐行 clips → record → finish → deliver。

queue.txt 每行：课号|标题|封面秒
  01|本福特定律|12

用法：
  CINE_ROOT=workspaces/vibe-knowledge/projects/my-film python cine/video/engines/queue.py
  ... queue.py --fps 30 --workers 4 --encoder x264

lock 防止两个队列同时写同一个 picture.mp4。
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

AIWORK = Path(__file__).resolve().parents[3]
ROOT = Path(os.environ.get("CINE_ROOT") or Path.cwd()).expanduser().resolve()
DOM = AIWORK / "cine/video/engines/dom"
FINISH = AIWORK / "workspaces/vibe-knowledge/line/dom-narrated/finish.py"
DELIVER = AIWORK / "cine/video/engines/deliver.py"


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def run(cmd, log):
    with log.open("a", encoding="utf-8", errors="replace") as f:
        f.write(f"\n$ {' '.join(map(str, cmd))}\n")
        f.flush()
        return subprocess.run(list(map(str, cmd)), stdout=f, stderr=subprocess.STDOUT).returncode


def main():
    fps = arg("--fps", None)
    if fps is None:
        try:
            fps = str(json.loads((ROOT / "project.json").read_text(encoding="utf-8")).get("fps", 30))
        except Exception:
            fps = "30"
    port = arg("--port", "8964")
    workers = arg("--workers", "1")
    encoder = arg("--encoder", "x264")
    queue = ROOT / "queue.txt"
    if not queue.exists():
        queue.write_text("# 课号|标题|封面秒\n", encoding="utf-8")
        print(f"✓ 已创建 {queue}，把要渲染的课写进去再跑。")
        return 0

    lock = ROOT / ".queue.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        raise SystemExit(f"另一个队列在跑（{lock}）；确认没有进程后删掉这个文件再试。")

    env = {**os.environ, "CINE_ROOT": str(ROOT)}
    done = failed = 0
    try:
        lines = [l.strip() for l in queue.read_text(encoding="utf-8").splitlines()]
        for line in lines:
            if not line or line.startswith("#"):
                continue
            parts = (line.split("|") + ["", "", ""])[:3]
            lesson, title, poster = parts[0].strip(), parts[1].strip() or parts[0].strip(), parts[2].strip() or "12"
            build = ROOT / "lessons" / lesson / "build"
            build.mkdir(parents=True, exist_ok=True)
            if (build / ".delivered").exists():
                print(f"- 跳过 {lesson}（已交付）")
                continue

            log = build / "queue.log"
            print(f"== {time.strftime('%H:%M')} 第 {lesson} 节：{title}")
            cmds = [
                [sys.executable, DOM / "clips.py", lesson, "--port", port],
                [sys.executable, DOM / "record.py", lesson, "--fps", fps, "--port", port,
                 "--workers", workers, "--encoder", encoder],
                [sys.executable, FINISH, lesson, "--fps", fps, "--port", port, "--encoder", encoder],
                [sys.executable, DELIVER, lesson, "--title", title, "--poster", poster],
            ]
            ok = True
            for cmd in cmds:
                code = run(cmd, log)
                if code != 0:
                    print(f"✗ 失败：{cmd[1].split(os.sep)[-1]}（看 {log}）")
                    ok = False
                    break
            if ok:
                (build / ".delivered").touch()
                done += 1
                print(f"✓ 完成 {lesson}")
            else:
                failed += 1
                break
    finally:
        try:
            lock.unlink()
        except OSError:
            pass

    print(f"队列结束：完成 {done}，失败 {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
