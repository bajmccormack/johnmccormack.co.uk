#!/usr/bin/env python3
"""Phase 5: 404 page, RSS snapshot, sitemaps, CNAME, robots, .nojekyll."""
import glob
import os
import re
import xml.etree.ElementTree as ET

OUT = "site"
RAW = "raw"
HOST = "johnmccormack.co.uk"
SITE = "https://" + HOST
PROBE = "this-page-does-not-exist-404-probe"


def build_404():
    """GitHub Pages serves /404.html for any unmatched path."""
    t = open("probe404.html", encoding="utf-8").read()
    t = t.replace(f"{SITE}/{PROBE}/", f"{SITE}/404.html")
    t = t.replace(PROBE, "")
    open(os.path.join(RAW, "404.html"), "w", encoding="utf-8").write(t)
    print("staged raw/404.html (rewrite pass will localise it)")


def build_feed():
    """Frozen snapshot of the RSS feed; the blog is no longer updated."""
    t = open("feed.xml", encoding="utf-8").read()
    # the feed advertises WP-only endpoints that will not exist statically
    t = re.sub(r"\s*<atom:link[^>]*rel=[\"']hub[\"'][^>]*/>", "", t)
    t = re.sub(r"\s*<link>\s*" + re.escape(SITE) + r"/xmlrpc\.php[^<]*</link>", "", t)
    t = t.replace(f"{SITE}/feed/", f"{SITE}/feed/index.xml")
    d = os.path.join(OUT, "feed")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.xml"), "w", encoding="utf-8").write(t)
    print(f"wrote {d}/index.xml ({len(t)} bytes)")


def exists_in_site(url):
    path = url.replace(SITE, "").split("?")[0]
    if not path.endswith("/"):
        path += "/"
    return os.path.exists(os.path.join(OUT, path.strip("/"), "index.html"))


def build_sitemaps():
    """Rebuild Yoast's sitemap set as static files, keeping original lastmod values."""
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    entries = []
    for f in sorted(glob.glob("sm-*.xml")):
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        for url in root.findall(f"{ns}url"):
            loc = url.findtext(f"{ns}loc")
            mod = url.findtext(f"{ns}lastmod")
            if loc and exists_in_site(loc):
                entries.append((loc, mod))
    seen, uniq = set(), []
    for loc, mod in entries:
        if loc not in seen:
            seen.add(loc)
            uniq.append((loc, mod))

    body = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"]
    for loc, mod in uniq:
        body.append("\t<url>\n\t\t<loc>%s</loc>%s\n\t</url>" %
                    (loc, f"\n\t\t<lastmod>{mod}</lastmod>" if mod else ""))
    body.append("</urlset>")
    open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(body))

    # keep the old index URL alive so existing search-engine references still resolve
    idx = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
           "<sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
           f"\t<sitemap>\n\t\t<loc>{SITE}/sitemap.xml</loc>\n\t</sitemap>\n"
           "</sitemapindex>\n")
    open(os.path.join(OUT, "sitemap_index.xml"), "w", encoding="utf-8").write(idx)
    print(f"wrote sitemap.xml ({len(uniq)} urls) + sitemap_index.xml")


def build_misc():
    open(os.path.join(OUT, "CNAME"), "w").write(HOST + "\n")
    open(os.path.join(OUT, ".nojekyll"), "w").write("")
    open(os.path.join(OUT, "robots.txt"), "w").write(
        "User-agent: *\nDisallow:\n\nSitemap: %s/sitemap.xml\n" % SITE)
    print("wrote CNAME, .nojekyll, robots.txt")


if __name__ == "__main__":
    build_404()
    build_feed()
    build_sitemaps()
    build_misc()
