#!/usr/bin/env python3
"""Phase 2: extract real asset URLs from the raw HTML cache and download them."""
import hashlib
import json
import os
import re
import threading
import queue
from urllib.parse import urljoin, urlsplit, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

SITE = "https://johnmccormack.co.uk"
HOST = "johnmccormack.co.uk"
RAW = "raw"
OUT = "site"

# rel values on <link> that point at a real downloadable asset
ASSET_LINK_RELS = {"stylesheet", "icon", "shortcut icon", "apple-touch-icon", "preload", "mask-icon"}
# never treat these as assets
SKIP_RE = re.compile(r"/(wp-json|xmlrpc\.php|wp-admin|wp-login)", re.I)

lock = threading.Lock()
found = {}      # absolute url -> set of source pages (for debugging)
local_map = {}  # absolute url -> local path relative to OUT


def add(url, base, bucket):
    if not url:
        return
    url = url.strip()
    if not url or url.startswith(("data:", "mailto:", "javascript:", "#", "about:")):
        return
    absu = urljoin(base, url)
    p = urlsplit(absu)
    if p.scheme not in ("http", "https"):
        return
    if SKIP_RE.search(p.path):
        return
    bucket.add(absu)


def srcset_urls(value, base, bucket):
    for part in value.split(","):
        u = part.strip().split()
        if u:
            add(u[0], base, bucket)


def page_url_for(raw_file):
    rel = os.path.relpath(raw_file, RAW)
    rel = rel[: -len("index.html")] if rel.endswith("index.html") else rel
    return SITE + "/" + rel.replace(os.sep, "/")


def extract_from_html():
    bucket = set()
    files = []
    for root, _, names in os.walk(RAW):
        for n in names:
            if n.endswith(".html"):
                files.append(os.path.join(root, n))
    for f in files:
        base = page_url_for(f)
        soup = BeautifulSoup(open(f, encoding="utf-8", errors="replace").read(), "lxml")
        for el in soup.find_all("img"):
            add(el.get("src"), base, bucket)
            add(el.get("data-src"), base, bucket)
            if el.get("srcset"):
                srcset_urls(el["srcset"], base, bucket)
        for el in soup.find_all("source"):
            add(el.get("src"), base, bucket)
            if el.get("srcset"):
                srcset_urls(el["srcset"], base, bucket)
        for el in soup.find_all(["video", "audio", "embed"]):
            add(el.get("src"), base, bucket)
            add(el.get("poster"), base, bucket)
        for el in soup.find_all("script", src=True):
            add(el["src"], base, bucket)
        for el in soup.find_all("link", href=True):
            rels = {r.lower() for r in (el.get("rel") or [])}
            if rels & ASSET_LINK_RELS:
                add(el["href"], base, bucket)
        # inline style="...url(x)..."
        for el in soup.find_all(style=True):
            for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)", el["style"]):
                add(m.group(1), base, bucket)
        # <style> blocks in <head> - this is where the theme's custom header
        # logo and other background images live
        for el in soup.find_all("style"):
            for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)", el.get_text()):
                add(m.group(1), base, bucket)
        # <a href> pointing at downloadable files kept on the site
        for el in soup.find_all("a", href=True):
            h = el["href"]
            if re.search(r"\.(pdf|pptx?|docx?|xlsx?|zip|sql|txt|csv|png|jpe?g|gif|svg|webp)$", h, re.I):
                absu = urljoin(base, h)
                if urlsplit(absu).netloc.lower().replace("www.", "") == HOST:
                    add(h, base, bucket)
    return bucket


def local_path_for(url):
    """Map an absolute asset URL to a path inside OUT."""
    p = urlsplit(url)
    host = p.netloc.lower()
    if host in (HOST, "www." + HOST):
        return unquote(p.path).lstrip("/")
    if "gravatar.com" in host:
        # avatar identity is hash + size; keep both
        h = p.path.rstrip("/").split("/")[-1]
        size = parse_qs(p.query).get("s", ["80"])[0]
        return f"assets/avatars/{h}-{size}.jpg"
    if "fonts.googleapis.com" in host:
        return "assets/fonts/google-fonts.css"
    if "fonts.gstatic.com" in host:
        return "assets/fonts/" + os.path.basename(p.path)
    # anything else stays remote
    return None


def download(url, dest, s):
    full = os.path.join(OUT, dest)
    if os.path.exists(full) and os.path.getsize(full) > 0:
        return "cached"
    os.makedirs(os.path.dirname(full), exist_ok=True)
    r = s.get(url, timeout=60)
    if r.status_code != 200:
        return f"HTTP {r.status_code}"
    with open(full, "wb") as fh:
        fh.write(r.content)
    return "ok"


def main():
    print("Scanning raw HTML for assets...", flush=True)
    urls = extract_from_html()
    print(f"  {len(urls)} candidate asset URLs", flush=True)

    todo = []
    for u in sorted(urls):
        lp = local_path_for(u)
        if lp:
            local_map[u] = lp
            todo.append((u, lp))
    print(f"  {len(todo)} to localise, {len(urls)-len(todo)} left remote", flush=True)

    results = {}
    q = queue.Queue()
    for item in todo:
        q.put(item)

    def worker():
        s = requests.Session()
        s.headers["User-Agent"] = "Mozilla/5.0 (static-archive-mirror; owner-authorised)"
        while True:
            try:
                u, lp = q.get(timeout=5)
            except queue.Empty:
                return
            try:
                res = download(u, lp, s)
            except Exception as e:  # noqa: BLE001
                res = repr(e)[:120]
            with lock:
                results[u] = res
                n = len(results)
            if n % 100 == 0:
                print(f"  {n}/{len(todo)}...", flush=True)
            q.task_done()

    ts = [threading.Thread(target=worker, daemon=True) for _ in range(12)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    bad = {u: r for u, r in results.items() if r not in ("ok", "cached")}
    json.dump({"local_map": local_map, "failures": bad},
              open("assets-state.json", "w", encoding="utf-8"), indent=1)
    print(f"\nDONE downloaded={len(results)-len(bad)} failed={len(bad)}")
    for u, r in list(bad.items())[:25]:
        print(f"  FAIL {r}  {u}")


if __name__ == "__main__":
    main()
