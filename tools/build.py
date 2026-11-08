#!/usr/bin/env python3
"""Build the upload-ready website into dist/.

- Minifies styles.css and script.js (smaller, faster downloads)
- Copies index.html, images, robots.txt and sitemap.xml
- Leaves out editing-only folders (brand/, tools/, .claude/) and notes

Run from the site folder:  tools/build
Then upload everything inside dist/ to your web host.
"""
import os
import re
import shutil
import sys

import rcssmin
import rjsmin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
COPY_FILES = ["index.html", "robots.txt", "sitemap.xml"]
COPY_DIRS = ["images"]


def kb(n):
    return f"{n / 1024:.1f} KB"


def main():
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)

    for name, minify in (("styles.css", rcssmin.cssmin), ("script.js", rjsmin.jsmin)):
        src = open(os.path.join(ROOT, name), encoding="utf-8").read()
        out = minify(src)
        if not out.strip():
            sys.exit(f"Minifying {name} produced nothing; stopping.")
        open(os.path.join(DIST, name), "w", encoding="utf-8").write(out)
        print(f"{name:12} {kb(len(src.encode())):>9} -> {kb(len(out.encode())):>9}")

    for name in COPY_FILES:
        shutil.copy2(os.path.join(ROOT, name), os.path.join(DIST, name))
    html = open(os.path.join(DIST, "index.html"), encoding="utf-8").read()
    # drop HTML comments (but never inside <script> blocks)
    parts = re.split(r"(<script\b.*?</script>)", html, flags=re.S)
    parts = [p if p.startswith("<script") else re.sub(r"<!--(?!\[).*?-->", "", p, flags=re.S) for p in parts]
    html_min = "".join(parts)
    html_min = re.sub(r"\n\s*\n+", "\n", html_min)
    open(os.path.join(DIST, "index.html"), "w", encoding="utf-8").write(html_min)
    print(f"{'index.html':12} {kb(len(html.encode())):>9} -> {kb(len(html_min.encode())):>9}")

    for d in COPY_DIRS:
        shutil.copytree(os.path.join(ROOT, d), os.path.join(DIST, d))
    total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(DIST) for f in fs)
    print(f"\nBuilt dist/ ({kb(total)} total). Upload the contents of dist/ to your host.")


if __name__ == "__main__":
    main()
