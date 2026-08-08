#!/usr/bin/env python3
"""Verify every local reference in the generated site resolves to a real file."""
import html as htmlmod
import os
import re
import sys
from collections import Counter, defaultdict
from urllib.parse import urlsplit, unquote

OUT = "site"
HOST = "johnmccormack.co.uk"
TAG_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>")
ATTR_RE = re.compile(r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(["'])(.*?)\2""", re.S)
URL_ATTRS = {"href", "src", "action", "poster"}

missing = defaultdict(set)      # target -> set of pages referencing it
abs_internal = defaultdict(set)
external = Counter()
ok = 0


def resolve(target):
    """Map a root-relative URL to an on-disk path candidate list."""
    p = unquote(urlsplit(target).path)
    base = os.path.join(OUT, p.lstrip("/"))
    if p.endswith("/"):
        return [os.path.join(base, "index.html")]
    return [base, os.path.join(base, "index.html"), base + ".html"]


def check_value(val, page, attr, tagname):
    global ok
    v = htmlmod.unescape(val.strip())
    if not v or v.startswith(("mailto:", "tel:", "javascript:", "data:", "#", "about:")):
        return
    sp = urlsplit(v)
    if sp.scheme in ("http", "https") or v.startswith("//"):
        host = sp.netloc.lower().split(":")[0]
        hn = host[4:] if host.startswith("www.") else host
        if hn == HOST:
            # canonical / og:url are deliberately absolute; flag anything else
            if not (tagname == "link" or attr == "content"):
                abs_internal[v].add(page)
        else:
            external[hn] += 1
        return
    if not v.startswith("/"):
        return  # relative-to-document; rare here, skip
    for cand in resolve(v):
        if os.path.exists(cand):
            ok += 1
            return
    missing[urlsplit(v).path].add(page)


def main():
    pages = 0
    for root, _, names in os.walk(OUT):
        for n in names:
            if not n.endswith(".html"):
                continue
            path = os.path.join(root, n)
            page = "/" + os.path.relpath(path, OUT).replace(os.sep, "/")
            text = open(path, encoding="utf-8", errors="replace").read()
            pages += 1
            for m in TAG_RE.finditer(text):
                tag, attrs = m.group(1).lower(), m.group(2)
                for am in ATTR_RE.finditer(attrs):
                    k, v = am.group(1).lower(), am.group(3)
                    if k == "srcset":
                        for part in v.split(","):
                            bits = part.strip().split()
                            if bits:
                                check_value(bits[0], page, k, tag)
                    elif k in URL_ATTRS:
                        check_value(v, page, k, tag)

    print(f"pages scanned      : {pages}")
    print(f"local refs resolved: {ok}")
    print(f"MISSING targets    : {len(missing)}")
    for t, pgs in sorted(missing.items(), key=lambda x: -len(x[1]))[:30]:
        print(f"   {len(pgs):5d} refs  {t}   e.g. {sorted(pgs)[0]}")
    print(f"\nabsolute internal (non-canonical): {len(abs_internal)}")
    for t, pgs in sorted(abs_internal.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"   {len(pgs):5d}  {t}")
    print("\ntop external hosts:")
    for h, c in external.most_common(12):
        print(f"   {c:6d}  {h}")


if __name__ == "__main__":
    main()
