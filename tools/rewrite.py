#!/usr/bin/env python3
"""Phase 3: rewrite the raw HTML cache into a static site.

String/tag-level rewriting only - never a full BeautifulSoup re-serialisation,
so text nodes and markup quirks stay byte-identical and the rendering cannot drift.
"""
import html as htmlmod
import os
import re
from urllib.parse import urlsplit, parse_qs, unquote

RAW = "raw"
OUT = "site"
HOST = "johnmccormack.co.uk"
DEAD = "johnmccormack.it"

# Attachment shortlinks that appear in post content -> pretty permalinks
ATTACHMENT_MAP = {
    "2644": "/2021/08/how-to-change-the-slow-query-log-threshold-on-rds/slow_query_log/",
    "2645": "/2021/08/how-to-change-the-slow-query-log-threshold-on-rds/long_query_time/",
}

ASSET_DIR_RE = re.compile(r"^/(wp-content|wp-includes|assets)/")
TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>")
ATTR_RE = re.compile(r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(["'])(.*?)\2""", re.S)

URL_ATTRS = {"href", "src", "action", "poster", "data-src", "data-lazy-src"}

stats = {
    "pages": 0, "links_rewritten": 0, "dead_domain_fixed": 0,
    "comment_forms_removed": 0, "reply_links_removed": 0,
    "head_links_dropped": 0, "gravatars": 0, "fonts": 0, "search_forms": 0,
}


# ---------------------------------------------------------------- URL mapping
def map_url(u, in_link_tag=False):
    """Map one URL to its static-site equivalent. Returns None to leave unchanged."""
    if not u:
        return None
    raw = u.strip()
    if raw.startswith(("mailto:", "tel:", "javascript:", "data:", "#")):
        return None

    unesc = htmlmod.unescape(raw)

    # Google Fonts -> local copy
    if "fonts.googleapis.com" in unesc:
        stats["fonts"] += 1
        return "/assets/fonts/google-fonts.css"

    # Gravatar -> local avatar
    if "gravatar.com/avatar/" in unesc:
        p = urlsplit(unesc)
        h = p.path.rstrip("/").split("/")[-1]
        size = parse_qs(p.query).get("s", ["80"])[0]
        stats["gravatars"] += 1
        return f"/assets/avatars/{h}-{size}.jpg"

    p = urlsplit(unesc)
    host = p.netloc.lower().split(":")[0]
    host_nw = host[4:] if host.startswith("www.") else host

    if host and host_nw not in (HOST, DEAD):
        return None  # genuinely third-party, leave alone
    if host_nw == DEAD:
        stats["dead_domain_fixed"] += 1

    path = p.path or "/"
    q = parse_qs(p.query)

    # search links -> client-side search page
    if "s" in q and path in ("/", ""):
        return "/search/?s=" + q["s"][0].replace(" ", "+")
    # attachment shortlinks -> pretty permalink
    if "attachment_id" in q:
        aid = q["attachment_id"][0]
        if aid in ATTACHMENT_MAP:
            return ATTACHMENT_MAP[aid]
    # dead endpoints
    if re.match(r"^/(wp-login\.php|xmlrpc\.php|wp-json|wp-comments-post\.php)", path):
        return "DROP"

    if not host and not p.query:
        return None  # already a clean relative URL - leave it

    # everything else: root-relative, query dropped (static host cannot vary on it)
    out = path
    if not ASSET_DIR_RE.match(path) and not re.search(r"\.[a-z0-9]{2,5}$", path):
        if not out.endswith("/"):
            out += "/"
    if p.fragment:
        out += "#" + p.fragment
    return out


# --------------------------------------------------------------- <link> tags
def handle_link_tag(attrs_src):
    """Return replacement text for a <link ...> tag, or None to drop it."""
    attrs = {k.lower(): v for k, v, in ((m.group(1), m.group(3))
             for m in ATTR_RE.finditer(attrs_src))}
    rel = (attrs.get("rel") or "").lower()
    href = attrs.get("href") or ""
    typ = (attrs.get("type") or "").lower()
    unesc = htmlmod.unescape(href)

    # WordPress plumbing that cannot exist on a static host
    if rel in ("edituri", "pingback", "shortlink", "https://api.w.org/", "wlwmanifest"):
        stats["head_links_dropped"] += 1
        return None
    if "oembed" in unesc or "/wp-json" in unesc or "xmlrpc.php" in unesc:
        stats["head_links_dropped"] += 1
        return None
    # comments feed: comments are closed on the static site
    if rel == "alternate" and "rss" in typ and "comments/feed" in unesc:
        stats["head_links_dropped"] += 1
        return None
    # main feed -> static snapshot
    if rel == "alternate" and "rss" in typ:
        return ("<link rel=\"alternate\" type=\"application/rss+xml\" "
                f"title={attrs.get('title', 'Feed')!r} href=\"/feed/index.xml\" />"
                .replace("'", '"'))
    # canonical / og stay absolute (correct for the live domain)
    if rel == "canonical":
        return "KEEP"
    return "KEEP"


# ------------------------------------------------------- comment form removal
def remove_div_by_id(text, div_id):
    """Remove <div id="X" ...> ... </div> with correct nesting. Returns (text, n)."""
    n = 0
    while True:
        m = re.search(r'<div[^>]*\bid=["\']' + re.escape(div_id) + r'["\'][^>]*>', text)
        if not m:
            return text, n
        start = m.start()
        i = m.end()
        depth = 1
        for t in re.finditer(r"<(/?)div\b[^>]*>", text[m.end():]):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                i = m.end() + t.end()
                break
        else:
            return text, n  # unbalanced; leave alone rather than corrupt
        text = text[:start] + text[i:]
        n += 1


def strip_comment_ui(text):
    text, n = remove_div_by_id(text, "respond")
    if n:
        stats["comment_forms_removed"] += n
    # per-comment "Reply" links now point at a form that no longer exists.
    # WordPress emits two wrapper variants depending on the comment template.
    for cls in ("reply", "comment-reply"):
        pat = r'<div class="' + cls + r'">.*?</div>'
        stats["reply_links_removed"] += len(re.findall(pat, text, flags=re.S))
        text = re.sub(pat, "", text, flags=re.S)
    # the script that moved the form around
    text = re.sub(r'<script[^>]*comment-reply[^>]*>\s*</script>', "", text)
    return text


# ------------------------------------------------------------- main rewriting
def rewrite_tag(m):
    closing, name, attrs_src = m.group(1), m.group(2).lower(), m.group(3)
    if closing:
        return m.group(0)

    if name == "link":
        res = handle_link_tag(attrs_src)
        if res is None:
            return ""
        if res != "KEEP":
            return res

    is_canonical = name == "link" and re.search(r'rel=["\']canonical["\']', attrs_src, re.I)

    def fix_attr(am):
        key, quote, val = am.group(1), am.group(2), am.group(3)
        kl = key.lower()

        if kl == "srcset":
            parts, changed = [], False
            for part in val.split(","):
                bits = part.strip().split()
                if not bits:
                    continue
                new = map_url(bits[0])
                if new and new != "DROP":
                    bits[0] = new
                    changed = True
                parts.append(" ".join(bits))
            if changed:
                stats["links_rewritten"] += 1
                return f'{key}={quote}{", ".join(parts)}{quote}'
            return am.group(0)

        if kl not in URL_ATTRS:
            return am.group(0)
        if is_canonical:
            return am.group(0)  # keep absolute

        new = map_url(val)
        if new is None:
            return am.group(0)
        if new == "DROP":
            new = "#"
        stats["links_rewritten"] += 1
        return f"{key}={quote}{new}{quote}"

    new_attrs = ATTR_RE.sub(fix_attr, attrs_src)
    return f"<{name}{new_attrs}>"


def rewrite_search_form(text):
    def sub(m):
        stats["search_forms"] += 1
        return m.group(0).replace(m.group(1), "/search/")
    return re.sub(r'<form[^>]*\brole=["\']search["\'][^>]*\baction=["\']([^"\']*)["\']',
                  sub, text)


def process(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    text = strip_comment_ui(text)
    text = TAG_RE.sub(rewrite_tag, text)
    text = rewrite_search_form(text)
    # any leftover absolute same-host refs inside inline <style> url(...)
    text = re.sub(r"url\((['\"]?)https?://" + re.escape(HOST) + r"(/[^'\")]*)",
                  lambda m: f"url({m.group(1)}{m.group(2).split('?')[0]}", text)
    return text


def main():
    files = []
    for root, _, names in os.walk(RAW):
        for n in names:
            if n.endswith(".html"):
                files.append(os.path.join(root, n))
    for f in sorted(files):
        rel = os.path.relpath(f, RAW)
        dest = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "w", encoding="utf-8").write(process(f))
        stats["pages"] += 1
    for k, v in stats.items():
        print(f"  {k:24s} {v}")


if __name__ == "__main__":
    main()
