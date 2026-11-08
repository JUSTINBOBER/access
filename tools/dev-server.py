#!/usr/bin/env python3
"""Local preview server for the Paws & Play site (for editing only, not for hosting).

- Never lets the browser use an old saved copy (no caching).
- Reloads open pages automatically whenever a site file changes,
  and keeps your scroll position.

Run from the site folder:  python3 tools/dev-server.py 8642
"""
import http.server
import os
import sys
import time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8642
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCH_EXT = {".html", ".css", ".js", ".webp", ".png", ".jpg", ".jpeg", ".svg", ".xml", ".txt"}
SKIP_DIRS = {".claude", "brand", "tools", ".git", "dist"}

RELOAD_SNIPPET = b"""<script>/* dev auto-reload (added by the preview server only) */
(() => {
  const key = "pp-dev-scroll:" + location.pathname;
  const y = sessionStorage.getItem(key);
  if (y !== null) {
    sessionStorage.removeItem(key);
    if ("scrollRestoration" in history) history.scrollRestoration = "manual";
    const restore = () => scrollTo({ top: +y, behavior: "instant" });
    // Keep trying for ~2s while images load and the page grows to full height
    let tries = 0;
    const timer = setInterval(() => {
      restore();
      if (Math.abs(scrollY - y) < 4 || ++tries > 20) clearInterval(timer);
    }, 100);
    addEventListener("wheel", () => clearInterval(timer), { once: true, passive: true });
    addEventListener("touchstart", () => clearInterval(timer), { once: true, passive: true });
  }
  const es = new EventSource("/__livereload");
  es.onmessage = () => { sessionStorage.setItem(key, scrollY); location.reload(); };
})();
</script>
"""


def latest_change():
    newest = 0.0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if os.path.splitext(name)[1].lower() in WATCH_EXT:
                try:
                    newest = max(newest, os.stat(os.path.join(dirpath, name)).st_mtime)
                except OSError:
                    pass
    return newest


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        if "/__livereload" not in (args[0] if args else ""):
            super().log_message(fmt, *args)

    def do_GET(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path == "/__livereload":
            return self.live_reload()
        if path.endswith("/"):
            path += "index.html"
        if path.endswith(".html"):
            return self.serve_html(path)
        return super().do_GET()

    def serve_html(self, path):
        file_path = self.translate_path(path)
        try:
            with open(file_path, "rb") as f:
                body = f.read()
        except OSError:
            return self.send_error(404, "File not found")
        marker = b"</body>"
        body = body.replace(marker, RELOAD_SNIPPET + marker, 1) if marker in body else body + RELOAD_SNIPPET
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def live_reload(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        seen = latest_change()
        last_ping = time.time()
        try:
            while True:
                time.sleep(0.4)
                now = latest_change()
                if now > seen:
                    time.sleep(0.25)  # let multi-file edits finish
                    self.wfile.write(b"data: reload\n\n")
                    self.wfile.flush()
                    return
                if time.time() - last_ping > 15:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    last_ping = time.time()
        except (BrokenPipeError, ConnectionResetError):
            return


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.daemon_threads = True
    print(f"Paws & Play preview running at http://localhost:{PORT} (auto-reload on)")
    server.serve_forever()
