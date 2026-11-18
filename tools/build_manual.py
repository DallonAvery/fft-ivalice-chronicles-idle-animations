"""Inline the manual's images so it is a single self-contained HTML file.

Reads docs/manual_src.html (English) and docs/manual_src_ru.html (Russian), whose images
are referenced as src="img/...", and writes docs/IdleAnimations_Manual_en.html and
docs/IdleAnimations_Manual_ru.html with every image embedded as a data: URI.
"""
import base64
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
TYPES = {".png": "image/png", ".gif": "image/gif", ".jpg": "image/jpeg"}


def inline(match):
    path = os.path.join(DOCS, match.group(1).replace("/", os.sep))
    data = base64.b64encode(open(path, "rb").read()).decode("ascii")
    return f'src="data:{TYPES[os.path.splitext(path)[1]]};base64,{data}"'


SOURCES = {"manual_src.html": "IdleAnimations_Manual_en.html",
           "manual_src_ru.html": "IdleAnimations_Manual_ru.html"}


def main():
    for src, name in SOURCES.items():
        html = open(os.path.join(DOCS, src), encoding="utf-8").read()
        out = re.sub(r'src="(img/[^"]+)"', inline, html)
        dst = os.path.join(DOCS, name)
        open(dst, "w", encoding="utf-8").write(out)
        print(dst, len(out.encode("utf-8")), "bytes")


if __name__ == "__main__":
    main()
