#!/usr/bin/env python3
"""Phase 1: crawl every public HTML page of johnmccormack.co.uk into a raw cache."""
import json
import os
import re
import sys
import threading
import queue
from urllib.parse import urljoin, urlparse, urlsplit

import requests
from bs4 import BeautifulSoup

SITE = "https://johnmccormack.co.uk"
HOST = "johnmccormack.co.uk"
DEAD_HOST = "johnmccormack.it"  # old domain, dead, same URL paths
RAW = "raw"
STATE = "crawl-state.json"

# Public pages only - no admin, no dynamic endpoints.
SKIP_PATH_RE = re.compile(
    r"^/(wp-admin|wp-login\.php|wp-cron\.php|xmlrpc\.php|wp-json|wp-signup|wp-trackback"
    r"|wp-comments-post\.php|wp-links-opml\.php|readme\.html|license\.txt)",
    re.I,
)
# Feed / dynamic variants we do not want as pages.
SKIP_SUFFIX_RE = re.compile(r"/(feed|embed|trackback)/?$", re.I)

ASSET_EXT_RE = re.compile(
    r"\.(css|js|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|eot|otf|mp4|webm|mp3|pdf|zip|txt|xml|json)$",
    re.I,
)

lock = threading.Lock()
seen = set()          # normalised page URLs enqueued
pages = {}            # url -> raw path
assets = set()        # absolute asset URLs discovered
failures = {}
q = queue.Queue()

session_local = threading.local()


def sess():
    if not hasattr(session_local, "s"):
        s = requests.Session()
        s.headers["User-Agent"] = "Mozilla/5.0 (static-archive-mirror; owner-authorised)"
        session_local.s = s
    return session_local.s


def normalise(url):
    """Canonicalise a URL to compare/dedupe. Returns None if not a crawlable page."""
    if not url:
        return None
    url = url.strip()
    if url.startswith(("mailto:", "tel:", "javascript:", "data:", "#")):
        return None
    url = urljoin(SITE + "/", url)
    p = urlsplit(url)
    if p.scheme not in ("http", "https"):
        return None
    host = p.netloc.lower().split(":")[0]
    if host == DEAD_HOST:
        host = HOST  # dead domain shares the same paths
    if host not in (HOST, "www." + HOST):
        return None
    path = p.path or "/"
    if SKIP_PATH_RE.match(path) or SKIP_SUFFIX_RE.search(path):
        return None
    # Drop every query string and fragment: static host cannot vary on them.
    if not path.endswith("/") and not ASSET_EXT_RE.search(path):
        path += "/"
    return "https://" + HOST + path


def is_asset(url):
    p = urlsplit(url)
    return bool(ASSET_EXT_RE.search(p.path))


def raw_path_for(url):
    path = urlsplit(url).path
    if path.endswith("/"):
        path += "index.html"
    return os.path.join(RAW, path.lstrip("/"))


def enqueue(url):
    n = normalise(url)
    if not n or is_asset(n):
        return
    with lock:
        if n in seen:
            return
        seen.add(n)
    q.put(n)


def collect_assets(soup, base):
    """Record every asset URL referenced by this page (any host)."""
    found = []
    for tag, attr in (
        ("img", "src"), ("script", "src"), ("link", "href"), ("source", "src"),
        ("video", "src"), ("audio", "src"), ("video", "poster"), ("embed", "src"),
    ):
        for el in soup.find_all(tag):
            v = el.get(attr)
            if v:
                found.append(urljoin(base, v))
            if tag in ("img", "source") and el.get("srcset"):
                for part in el["srcset"].split(","):
                    u = part.strip().split(" ")[0]
                    if u:
                        found.append(urljoin(base, u))
    with lock:
        for f in found:
            p = urlsplit(f)
            if p.scheme in ("http", "https"):
                assets.add(f)


def worker():
    while True:
        try:
            url = q.get(timeout=5)
        except queue.Empty:
            return
        try:
            r = sess().get(url, timeout=45, allow_redirects=True)
            ctype = r.headers.get("content-type", "")
            if r.status_code != 200:
                with lock:
                    failures[url] = r.status_code
                continue
            if "text/html" not in ctype:
                continue

            dest = raw_path_for(url)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(r.text)
            with lock:
                pages[url] = dest
                n = len(pages)
            if n % 25 == 0:
                print(f"  {n} pages...", flush=True)

            soup = BeautifulSoup(r.text, "lxml")
            collect_assets(soup, url)
            for a in soup.find_all("a", href=True):
                enqueue(a["href"])
            # rel=next/prev drive archive pagination
            for l in soup.find_all("link", rel=True, href=True):
                if any(x in ("next", "prev") for x in l.get("rel", [])):
                    enqueue(l["href"])
        except Exception as e:  # noqa: BLE001
            with lock:
                failures[url] = repr(e)[:200]
        finally:
            q.task_done()


def main():
    os.makedirs(RAW, exist_ok=True)
    enqueue(SITE + "/")
    for line in open("all-urls.txt", encoding="utf-8"):
        enqueue(line.strip())
    print(f"Seeded {q.qsize()} URLs from sitemaps + homepage", flush=True)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    json.dump(
        {"pages": pages, "assets": sorted(assets), "failures": failures},
        open(STATE, "w", encoding="utf-8"),
        indent=1,
    )
    print(f"\nDONE  pages={len(pages)}  assets={len(assets)}  failures={len(failures)}")
    if failures:
        for u, e in list(failures.items())[:15]:
            print(f"  FAIL {u} -> {e}")


if __name__ == "__main__":
    main()
