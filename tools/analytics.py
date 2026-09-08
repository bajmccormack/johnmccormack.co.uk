#!/usr/bin/env python3
"""Add (or remove) the Google Analytics tag across the static site.

The tag is purely additive: a comment and two <script> tags immediately
after the opening <head>, where Google asks for it, and nothing else. No
existing markup is rewritten, so --revert restores every page
byte-for-byte.

To point the site at a different property, edit MEASUREMENT_ID below and
run the script again: a page already carrying a different id is rewritten
rather than skipped.

    python3 tools/analytics.py            # add
    python3 tools/analytics.py --revert   # remove
    python3 tools/analytics.py --check    # report only, change nothing
"""
import os
import re
import sys

# ---------------------------------------------------------------------------
MEASUREMENT_ID = "G-HH7H2EHH08"
# ---------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "tools"}

# Google's own snippet, with ids added on the two tags so the removal
# regex below has something unambiguous to match.
BLOCK = (
    "<!-- Google tag (gtag.js) -->\n"
    "<script async id='jm-ga-lib'"
    f' src="https://www.googletagmanager.com/gtag/js?id={MEASUREMENT_ID}"></script>\n'
    "<script id='jm-ga-init'>\n"
    "  window.dataLayer = window.dataLayer || [];\n"
    "  function gtag(){dataLayer.push(arguments);}\n"
    "  gtag('js', new Date());\n"
    "\n"
    f"  gtag('config', '{MEASUREMENT_ID}');\n"
    "</script>\n"
)

BLOCK_RE = re.compile(
    r"[ \t]*<!-- Google tag \(gtag\.js\) -->\n?"
    r"|[ \t]*<script async id='jm-ga-lib'[^>]*></script>\n?"
    r"|[ \t]*<script id='jm-ga-init'>.*?</script>\n?",
    re.S,
)

HEAD_RE = re.compile(r"<head\b[^>]*>")

stats = {"pages": 0, "added": 0, "removed": 0, "unchanged": 0}


def html_files():
    """Every page of the site, the oEmbed cards included.

    /<post>/embed/ pages carry no site chrome, so the dark mode and banner
    layers skip them, but they are still pages served from the domain and
    their views count.
    """
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".html"):
                yield os.path.join(dirpath, fn)


def add(text):
    if BLOCK in text:
        return text, False
    # A tag for some other property, or an older shape of this one: take it
    # off first so the page ends up with exactly one.
    text, removed = BLOCK_RE.subn("", text)
    m = HEAD_RE.search(text)
    if not m:
        return text, False
    # Go in after the newline that ends the <head> line, not before it, so
    # the block owns every line it adds and --revert takes them all back.
    at = m.end() + (1 if text[m.end():m.end() + 1] == "\n" else 0)
    text = text[:at] + BLOCK + text[at:]
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
    print(f"  tag added       : {stats['added']}")
    print(f"  tag removed     : {stats['removed']}")
    print(f"  already correct : {stats['unchanged']}")


if __name__ == "__main__":
    main()
