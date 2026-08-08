#!/usr/bin/env python3
"""Phase 4b: turn the live 'no results' search page into a client-side search page.

Using the real WordPress-rendered page as the shell guarantees the header, nav,
footer and typography are identical to every other page on the site.
"""
import os
import re

SRC = "search-none.html"
DEST = os.path.join("raw", "search", "index.html")
PROBE = "zzqqxxnothinghere"

SEARCH_UI = '''<div class="archive-description"><h1 class="archive-title">Search</h1></div>
<div class="entry" id="jm-search-box"><form role="search" method="get" action="/search/" class="wp-block-search__button-outside wp-block-search__text-button wp-block-search"><label class="wp-block-search__label screen-reader-text" for="jm-search-input">Search</label><div class="wp-block-search__inside-wrapper"><input class="wp-block-search__input" id="jm-search-input" placeholder="Search johnmccormack.co.uk" value="" type="search" name="s" required /><button aria-label="Search" class="wp-block-search__button wp-element-button" type="submit">Search</button></div></form></div>
<div id="jm-search-results"></div></main>'''

SCRIPT = r'''<script id="jm-search-js">
(function () {
  var MONTHS = ["January","February","March","April","May","June","July",
                "August","September","October","November","December"];
  function ord(n) {
    if (n > 3 && n < 21) return "th";
    return ["th","st","nd","rd"][n % 10] || "th";
  }
  function fmtDate(iso) {
    var p = iso.split("-"), d = parseInt(p[2], 10);
    return d + ord(d) + " " + MONTHS[parseInt(p[1], 10) - 1] + " " + p[0];
  }
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function param(name) {
    var m = new RegExp("[?&]" + name + "=([^&#]*)").exec(location.search);
    return m ? decodeURIComponent(m[1].replace(/\+/g, " ")) : "";
  }
  function count(hay, needle) {
    var n = 0, i = 0;
    while ((i = hay.indexOf(needle, i)) !== -1) { n++; i += needle.length; }
    return n;
  }

  var q = (param("s") || param("q")).trim();
  var titleEl = document.querySelector(".archive-title");
  var out = document.getElementById("jm-search-results");
  var input = document.getElementById("jm-search-input");
  if (input && q) input.value = q;
  if (!q) return;

  document.title = "You searched for " + q + " - John McCormack DBA";
  if (titleEl) titleEl.textContent = "Search Results for: " + q;

  var terms = q.toLowerCase().split(/\s+/).filter(Boolean);

  function render(docs) {
    if (!docs.length) {
      out.innerHTML = '<div class="entry"><p>Sorry, no content matched your criteria.</p></div>';
      document.body.classList.add("search-no-results");
      return;
    }
    var html = docs.map(function (d) {
      return '<article class="post type-post status-publish format-standard entry" aria-label="' +
        esc(d.t) + '"><header class="entry-header"><h2 class="entry-title">' +
        '<a class="entry-title-link" rel="bookmark" href="' + esc(d.u) + '">' + esc(d.t) +
        '</a></h2> <p class="entry-meta"><time class="entry-time">' + fmtDate(d.d) +
        '</time> By <span class="entry-author"><a href="/author/jmccorma/" ' +
        'class="entry-author-link" rel="author"><span class="entry-author-name">' +
        'John McCormack</span></a></span></p></header><div class="entry-content"><p>' +
        esc(d.e) + '</p></div></article>';
    }).join("");
    out.innerHTML = html;
  }

  var xhr = new XMLHttpRequest();
  xhr.open("GET", "/search-index.json", true);
  xhr.onload = function () {
    if (xhr.status !== 200) {
      out.innerHTML = '<div class="entry"><p>Search is temporarily unavailable.</p></div>';
      return;
    }
    var docs = JSON.parse(xhr.responseText);
    var scored = [];
    for (var i = 0; i < docs.length; i++) {
      var d = docs[i], s = 0, ok = true;
      var t = d.t.toLowerCase(), k = (d.k || "").toLowerCase();
      for (var j = 0; j < terms.length; j++) {
        var term = terms[j], hit = false;
        if (t.indexOf(term) !== -1) { s += 25; hit = true; }
        if (k.indexOf(term) !== -1) { s += 8; hit = true; }
        var c = count(d.b, term);
        if (c) { s += Math.min(c, 12); hit = true; }
        if (!hit) { ok = false; break; }
      }
      if (ok) { d._s = s; scored.push(d); }
    }
    scored.sort(function (a, b) { return b._s - a._s || (a.d < b.d ? 1 : -1); });
    render(scored);
  };
  xhr.onerror = function () {
    out.innerHTML = '<div class="entry"><p>Search is temporarily unavailable.</p></div>';
  };
  xhr.send();
})();
</script>'''


def main():
    t = open(SRC, encoding="utf-8").read()

    # neutralise the probe term everywhere it leaked into metadata
    t = t.replace("You searched for " + PROBE, "Search")
    t = t.replace("/search/" + PROBE + "/", "/search/")
    t = t.replace(PROBE, "")

    # swap the static no-results body for the live search UI
    block = re.search(r'<div class="archive-description">.*?</main>', t, re.S)
    assert block, "could not locate content block"
    t = t[: block.start()] + SEARCH_UI + t[block.end():]

    # keep search pages out of the index, as WordPress did
    if "<title>" in t and 'name="robots"' not in t:
        t = t.replace("<title>", '<meta name="robots" content="noindex,follow" />\n<title>', 1)

    t = t.replace("</body>", SCRIPT + "\n</body>", 1)
    t = t.replace(' search-no-results ', ' ')

    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    open(DEST, "w", encoding="utf-8").write(t)
    print(f"wrote {DEST} ({len(t)} bytes)")


if __name__ == "__main__":
    main()
