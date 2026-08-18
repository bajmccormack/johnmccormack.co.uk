#!/usr/bin/env python3
"""Add, update or remove the site notice banner across the static site.

To change the notice, edit BANNER_TEXT below and run the script again. The
banner's id is derived from the text, so the new notice is shown again to
readers who dismissed the previous one.

    python3 tools/banner.py            # add or update
    python3 tools/banner.py --revert   # remove
    python3 tools/banner.py --check    # report only, change nothing
"""
import hashlib
import os
import re
import sys

# ---------------------------------------------------------------------------
# The notice. Plain text; use HTML entities for anything non-ASCII.
# ---------------------------------------------------------------------------
BANNER_TEXT = ("Blogging is currently blocked by a long-running process "
               "called &#8220;life&#8221;.")
# ---------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "tools"}

BANNER_ID = hashlib.sha1(BANNER_TEXT.encode("utf-8")).hexdigest()[:8]

BANNER = (
    f'<div class="jm-banner" data-banner="{BANNER_ID}">'
    f'<p class="jm-banner-text">'
    f'<span class="jm-banner-message">{BANNER_TEXT}</span>'
    f'</p></div>'
)

# Hides an already-dismissed notice before the first paint. Nothing inside
# the banner nests a <div>, so the markup regex below stays unambiguous.
BOOT = (
    "<script id='jm-banner-boot'>"
    "(function(){try{"
    f"if(localStorage.getItem('jm-banner-dismissed')==='{BANNER_ID}')"
    "document.documentElement.classList.add('jm-banner-hidden');"
    "}catch(e){}})();"
    "</script>\n"
)
CSS = ("<link rel='stylesheet' id='jm-banner-css'"
       " href='/assets/css/banner.css' media='all' />\n")
JS = "<script id='jm-banner-js' src='/assets/js/banner.js' defer></script>\n"

HEAD_BLOCK = BOOT + CSS + JS

HEAD_RE = re.compile(
    r"[ \t]*<script id='jm-banner-boot'>.*?</script>\n?"
    r"|[ \t]*<link rel='stylesheet' id='jm-banner-css'[^>]*>\n?"
    r"|[ \t]*<script id='jm-banner-js'[^>]*></script>\n?",
    re.S,
)
BANNER_RE = re.compile(r'<div class="jm-banner"[^>]*>.*?</div>', re.S)
BODY_RE = re.compile(r"(<body\b[^>]*>)")

stats = {"pages": 0, "added": 0, "updated": 0, "removed": 0, "unchanged": 0}


def html_files():
    """Every page of the site except the oEmbed cards.

    /<post>/embed/ pages are self-contained iframe widgets with no site
    chrome, so the notice does not belong on them.
    """
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and d != "embed"]
        for fn in filenames:
            if fn.endswith(".html"):
                yield os.path.join(dirpath, fn)


def add(text):
    original = text
    had_banner = BANNER_RE.search(text) is not None

    # Head block: rewritten only when it is missing or carries a stale id,
    # so re-running does not shuffle these tags past other layers' tags.
    head_current = (
        f"'jm-banner-dismissed')==='{BANNER_ID}'" in text
        and "id='jm-banner-css'" in text
        and "id='jm-banner-js'" in text
    )
    if not head_current:
        text = HEAD_RE.sub("", text)
        if "</head>" in text:
            text = text.replace("</head>", HEAD_BLOCK + "</head>", 1)

    # Banner markup, first thing in <body>.
    if had_banner:
        text = BANNER_RE.sub(lambda m: BANNER, text, count=1)
    else:
        text = BODY_RE.sub(lambda m: m.group(1) + BANNER, text, count=1)

    if text == original:
        return text, False
    stats["updated" if had_banner else "added"] += 1
    return text, True


def remove(text):
    original = text
    text = HEAD_RE.sub("", text)
    text = BANNER_RE.sub("", text)
    if text == original:
        return text, False
    stats["removed"] += 1
    return text, True


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

    verb = {"add": "applied", "revert": "reverted", "check": "would change"}[mode]
    print(f"{verb}: {stats['pages']} pages scanned, "
          f"{stats['pages'] - stats['unchanged']} touched")
    print(f"  notice id       : {BANNER_ID}")
    print(f"  banner added    : {stats['added']}")
    print(f"  banner updated  : {stats['updated']}")
    print(f"  banner removed  : {stats['removed']}")
    print(f"  already correct : {stats['unchanged']}")


if __name__ == "__main__":
    main()
