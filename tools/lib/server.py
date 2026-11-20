#!/usr/bin/env python3
"""本地静态服务器：项目根 + 共享引擎 + 资源池。

URL 约定：
  /cine/index.html            DOM 引擎入口（映射到 cine/video/engines/dom/index.html）
  /cine/video/...             共享引擎（canonical）
  /cine/engine/...            旧路径别名 → cine/video/engines/dom
  /cine/canvas/...            旧路径别名 → cine/video/engines/canvas
  /cine/fonts/...             旧路径别名 → resources/fonts
  /cine/audio/sfx/...         旧路径别名 → resources/sfx
  /resources/...              资源池
  其它                        项目根（CINE_ROOT）

record.py / stills.py / finish.py 会自动调用 serve()；也可以手动：
  python tools/lib/server.py --root workspaces/vibe-knowledge/projects/my-film --port 8964
"""
import argparse
import contextlib
import http.server
import socket
import threading
import time
import urllib.parse
from pathlib import Path

AIWORK = Path(__file__).resolve().parents[2]
RESOURCES = AIWORK / "resources"


def _safe_join(base: Path, rel: str) -> Path:
    """丢掉空段和 ..，避免路径穿越。"""
    parts = [p for p in urllib.parse.unquote(rel).split("/") if p not in ("", ".", "..")]
    return base.joinpath(*parts)


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".css": "text/css",
        ".json": "application/json",
        ".ttf": "font/ttf",
        ".woff2": "font/woff2",
        ".svg": "image/svg+xml",
    }

    def __init__(self, *args, root: Path, engine: Path, **kwargs):
        self.root = Path(root).resolve()
        self.engine = Path(engine).resolve()
        super().__init__(*args, directory=str(self.root), **kwargs)

    def translate_path(self, path):
        raw = urllib.parse.urlsplit(path).path

        if raw in ("/cine", "/cine/", "/cine/index.html"):
            return str(self.engine / "video/engines/dom/index.html")

        if raw == "/resources" or raw.startswith("/resources/"):
            return str(_safe_join(RESOURCES, raw[len("/resources"):]))

        # /line/<workspace>/<line>/... → workspaces/<workspace>/line/<line>/...
        if raw.startswith("/line/"):
            parts = [p for p in raw[len("/line/"):].split("/") if p]
            if len(parts) >= 3:
                base = AIWORK / "workspaces" / parts[0] / "line" / parts[1]
                return str(_safe_join(base, "/".join(parts[2:])))

        if raw.startswith("/cine/"):
            rel = raw[len("/cine/"):]
            # 旧项目里的 film.js / film.canvas.js 仍写 ../../cine/engine|canvas，
            # 这里做别名，项目文件不需要跟着引擎搬家。
            aliases = (
                ("engine/", self.engine / "video/engines/dom", 7),
                ("canvas/", self.engine / "video/engines/canvas", 7),
                ("fonts/", RESOURCES / "fonts", 6),
                ("audio/sfx/", RESOURCES / "sfx", 10),
            )
            for prefix, base, cut in aliases:
                if rel.startswith(prefix):
                    return str(_safe_join(base, rel[cut:]))
            return str(_safe_join(self.engine, rel))

        return str(_safe_join(self.root, raw))

    def log_message(self, fmt, *args):
        pass


def is_up(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False


@contextlib.contextmanager
def serve(port: int, root: Path, engine: Path | None = None):
    """确保 127.0.0.1:port 有服务器；端口已占用则直接复用。"""
    port = int(port)
    if is_up(port):
        yield False
        return

    root = Path(root).expanduser().resolve()
    engine = Path(engine or AIWORK / "cine").expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"CINE_ROOT 不是目录：{root}")
    if not (engine / "video/engines/dom/index.html").exists():
        raise FileNotFoundError(f"引擎目录缺少 video/dom/index.html：{engine}")

    def factory(*args, **kwargs):
        return Handler(*args, root=root, engine=engine, **kwargs)

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), factory)
    httpd.daemon_threads = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True, name=f"cine-http-{port}")
    t.start()
    try:
        yield True
    finally:
        httpd.shutdown()
        httpd.server_close()
        t.join(timeout=5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="项目根（CINE_ROOT）")
    ap.add_argument("--port", type=int, default=8964)
    ap.add_argument("--engine", default=None)
    args = ap.parse_args()
    with serve(args.port, Path(args.root), Path(args.engine) if args.engine else None):
        print(f"http://127.0.0.1:{args.port}/cine/index.html  root={Path(args.root).resolve()}")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
