#!/usr/bin/env python3
"""Add (or remove) the dark mode layer across the static site.

The layer is purely additive: three tags at the end of <head> and nothing
else. No existing markup is rewritten, so --revert restores every page
byte-for-byte.

    python3 tools/darkmode.py            # add
    python3 tools/darkmode.py --revert   # remove
    python3 tools/darkmode.py --check    # report only, change nothing
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "tools"}

# Reads the stored choice and sets it on <html> before the first paint, so
# there is no flash of the wrong scheme. When nothing is stored it does
# nothing and the stylesheet's prefers-color-scheme rules decide.
BOOT = (
    "<script id='jm-darkmode-boot'>"
    "(function(){try{var t=localStorage.getItem('jm-theme');"
    "if(t==='dark'||t==='light')"
    "document.documentElement.setAttribute('data-theme',t);}catch(e){}})();"
    "</script>\n"
)
CSS = ("<link rel='stylesheet' id='jm-darkmode-css'"
       " href='/assets/css/darkmode.css' media='all' />\n")
JS = "<script id='jm-darkmode-js' src='/assets/js/darkmode.js' defer></script>\n"

BLOCK = BOOT + CSS + JS

BLOCK_RE = re.compile(
    r"[ \t]*<script id='jm-darkmode-boot'>.*?</script>\n?"
    r"|[ \t]*<link rel='stylesheet' id='jm-darkmode-css'[^>]*>\n?"
    r"|[ \t]*<script id='jm-darkmode-js'[^>]*></script>\n?",
    re.S,
)

stats = {"pages": 0, "added": 0, "removed": 0, "unchanged": 0}


def html_files():
    """Every page of the site except the oEmbed cards.

    /<post>/embed/ pages are self-contained iframe widgets with their own
    markup and no site chrome, so the layer does not apply to them.
    """
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and d != "embed"]
        for fn in filenames:
            if fn.endswith(".html"):
                yield os.path.join(dirpath, fn)


def add(text):
    if "id='jm-darkmode-css'" in text or "</head>" not in text:
        return text, False
    text = text.replace("</head>", BLOCK + "</head>", 1)
    stats["added"] += 1
    return text, True


def remove(text):
    text, n = BLOCK_RE.subn("", text)
    if n:
        stats["removed"] += 1
    return text, bool(n)


def main():
    mode = "add"
    if "--revert" in sys.argv:
        mode = "revert"
    elif "--check" in sys.argv:
        mode = "check"

    action = remove if mode == "revert" else add

    for path in html_files():
        stats["pages"] += 1
        with open(path, encoding="utf-8") as fh:
            text = fh.read()

        new, changed = action(text)

        if not changed:
            stats["unchanged"] += 1
            continue
        if mode == "check":
            continue
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new)

    verb = {"add": "added", "revert": "reverted", "check": "would change"}[mode]
    print(f"{verb}: {stats['pages']} pages scanned, "
          f"{stats['pages'] - stats['unchanged']} touched")
    print(f"  layer added     : {stats['added']}")
    print(f"  layer removed   : {stats['removed']}")
    print(f"  already correct : {stats['unchanged']}")


if __name__ == "__main__":
    main()
