#!/usr/bin/env python3
"""Phase 2b: download assets referenced from inside CSS, and localise Google Fonts."""
import os
import re
import requests
from urllib.parse import urljoin, urlsplit, unquote

SITE = "https://johnmccormack.co.uk"
OUT = "site"
BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/126.0 Safari/537.36")

s = requests.Session()
s.headers["User-Agent"] = BROWSER_UA

URL_RE = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""")


def local_to_url(local_css):
    """site/wp-includes/css/x.css -> https://host/wp-includes/css/x.css"""
    rel = os.path.relpath(local_css, OUT).replace(os.sep, "/")
    return f"{SITE}/{rel}"


def fetch_css_assets():
    got, failed = 0, []
    for root, _, names in os.walk(OUT):
        for n in names:
            if not n.endswith(".css"):
                continue
            path = os.path.join(root, n)
            if "/assets/fonts/" in path.replace(os.sep, "/"):
                continue  # handled by google fonts step
            base = local_to_url(path)
            css = open(path, encoding="utf-8", errors="replace").read()
            for _, ref in URL_RE.findall(css):
                ref = ref.strip()
                if not ref or ref.startswith(("data:", "#", "http://", "https://", "//")):
                    continue
                absu = urljoin(base, ref)
                p = urlsplit(absu)
                dest = os.path.join(OUT, unquote(p.path).lstrip("/"))
                if os.path.exists(dest) and os.path.getsize(dest) > 0:
                    continue
                try:
                    r = s.get(absu.split("#")[0], timeout=60)
                    if r.status_code == 200:
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        open(dest, "wb").write(r.content)
                        got += 1
                        print(f"  + {os.path.relpath(dest, OUT)} ({len(r.content)}b)")
                    else:
                        failed.append((absu, r.status_code))
                except Exception as e:  # noqa: BLE001
                    failed.append((absu, repr(e)[:80]))
    print(f"CSS assets: {got} downloaded, {len(failed)} failed")
    for u, e in failed:
        print(f"  FAIL {e} {u}")


def localise_google_fonts():
    """Re-fetch with a browser UA so we get woff2, then pull the font files local."""
    src = ("https://fonts.googleapis.com/css"
           "?family=Lato%3A300%2C400%7CMerriweather%3A400%2C300&ver=2.1")
    r = s.get(src, timeout=60)
    r.raise_for_status()
    css = r.text
    fonts = set(re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css))
    print(f"Google Fonts: {len(fonts)} font files, format={'woff2' if 'woff2' in css else 'ttf'}")
    outdir = os.path.join(OUT, "assets", "fonts")
    os.makedirs(outdir, exist_ok=True)
    for f in sorted(fonts):
        name = os.path.basename(urlsplit(f).path)
        dest = os.path.join(outdir, name)
        if not (os.path.exists(dest) and os.path.getsize(dest) > 0):
            fr = s.get(f, timeout=60)
            fr.raise_for_status()
            open(dest, "wb").write(fr.content)
        css = css.replace(f, name)  # same directory as the css file
        print(f"  + assets/fonts/{name}")
    open(os.path.join(outdir, "google-fonts.css"), "w", encoding="utf-8").write(css)
    print("  wrote assets/fonts/google-fonts.css")


if __name__ == "__main__":
    fetch_css_assets()
    localise_google_fonts()
