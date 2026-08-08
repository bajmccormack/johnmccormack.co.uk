#!/usr/bin/env python3
"""Phase 4: build the client-side search index from the WordPress REST API."""
import html as htmlmod
import json
import os
import re
import requests

SITE = "https://johnmccormack.co.uk"
OUT = "site"

s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0 (static-archive-mirror; owner-authorised)"


def fetch_all(kind, fields):
    out, page = [], 1
    while True:
        r = s.get(f"{SITE}/wp-json/wp/v2/{kind}",
                  params={"per_page": 100, "page": page, "_fields": fields}, timeout=60)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        out += batch
        if len(batch) < 100:
            break
        page += 1
    return out


def terms(kind):
    return {t["id"]: t["name"] for t in fetch_all(kind, "id,name")}


def strip_html(h):
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S | re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    h = htmlmod.unescape(h)
    return re.sub(r"\s+", " ", h).strip()


def main():
    cats, tags = terms("categories"), terms("tags")
    posts = fetch_all("posts", "id,link,title,excerpt,content,date,categories,tags")
    pages = fetch_all("pages", "id,link,title,excerpt,content,date")
    print(f"posts={len(posts)} pages={len(pages)} cats={len(cats)} tags={len(tags)}")

    docs = []
    for p in posts + pages:
        body = strip_html(p.get("content", {}).get("rendered", ""))
        title = htmlmod.unescape(strip_html(p["title"]["rendered"]))
        exc = strip_html(p.get("excerpt", {}).get("rendered", ""))
        exc = re.sub(r"\s*(Continue Reading|Read More).*$", "", exc).strip()
        if not exc:
            exc = body[:220]
        if len(exc) > 260:
            exc = exc[:257].rsplit(" ", 1)[0] + "..."
        tnames = [cats.get(i, "") for i in p.get("categories", [])] + \
                 [tags.get(i, "") for i in p.get("tags", [])]
        tnames = [t for t in tnames if t]
        url = p["link"].replace(SITE, "") or "/"
        docs.append({
            "t": title,
            "u": url,
            "d": p["date"][:10],
            "e": exc,
            "k": " ".join(tnames),
            "b": body.lower(),
        })

    docs.sort(key=lambda d: d["d"], reverse=True)
    path = os.path.join(OUT, "search-index.json")
    json.dump(docs, open(path, "w", encoding="utf-8"), separators=(",", ":"))
    size = os.path.getsize(path)
    print(f"wrote {path}  {len(docs)} docs  {size/1024:.0f} KB")


if __name__ == "__main__":
    main()
