# johnmccormack.co.uk — static archive

A fully static snapshot of the WordPress site **John McCormack DBA**, built to be served
from GitHub Pages so the EC2 + RDS + ELB stack can be shut down.

Captured from the live site on **8 August 2026**.

| | |
|---|---|
| HTML pages | 678 |
| Posts / pages | 105 / 2 |
| Categories / tags | 59 / 207 |
| Comments preserved | 56 (incl. trackbacks) |
| Images & other assets | ~590 |
| Total size | 116 MB |

Everything is plain HTML/CSS/JS. There is no build step and no server-side code.

---

## Deploying to GitHub Pages

1. Push this directory to a GitHub repo.
2. **Settings → Pages → Source:** *Deploy from a branch*, branch `main`, folder `/ (root)`.
3. **Settings → Pages → Custom domain:** `johnmccormack.co.uk` (the `CNAME` file already
   contains this), then tick **Enforce HTTPS** once the certificate is issued.
4. Point DNS at GitHub Pages, replacing the current AWS records:

   | Type | Name | Value |
   |---|---|---|
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | CNAME | `www` | `<username>.github.io` |

Only tear down the AWS stack once the site resolves correctly on the new DNS.

### Why the odd-looking files matter

- **`.nojekyll`** — required. Without it GitHub runs Jekyll, which silently drops
  `wp-content/plugins/akismet/_inc/` (directories beginning with `_`).
- **`CNAME`** — holds the custom domain. GitHub rewrites this if you change the domain
  in Settings; keep the two in sync.

---

## URLs are unchanged

Every original permalink still resolves, because each page is stored at its own path
(`/2019/03/put-tempdb-files-on-d-drive-in-azure-iaas/index.html`). Inbound links,
bookmarks and search-engine results keep working. `sitemap.xml` and `sitemap_index.xml`
are regenerated with the original `lastmod` values.

---

## What changed, and why

Appearance is unchanged — the rendered homepage is **pixel-identical** to the live site.
The differences are confined to things that cannot work without PHP and a database:

| Change | Reason |
|---|---|
| Comment form removed | Nothing can accept a POST. Existing comments still display in full. |
| Per-comment "Reply" links removed | They only existed to move the now-absent form. |
| Search rebuilt client-side | See below. |
| `wp-json`, `xmlrpc.php`, RSD, pingback and shortlink tags dropped | Dead endpoints. |
| RSS feed frozen at `/feed/index.xml` | A static snapshot; the old `/feed/` path no longer resolves. |
| Google Fonts + Gravatar avatars downloaded locally | Removes third-party runtime dependencies. |
| `johnmccormack.it` links repointed to `.co.uk` | That domain is dead; the paths are identical, so 61 previously-broken links now work. Visible link *text* was left untouched. |

### Search

The search box works. `/search/` is the real WordPress search template with a small
script that queries `search-index.json` (107 documents, 391 KB — 121 KB gzipped),
matching on title, tags/categories and full body text, ranked by relevance.
`?s=` URLs behave as before, so old search links still work.

---

## Known issues (all pre-existing — these were already broken on the live site)

- **5 images are permanently lost.** They 404 on the live server and are not in the
  Wayback Machine. Four are referenced under an old `/blog/` path prefix:
  `LiteSpeed_Backup_Savings.png`, `Drivespace_DMF.png`,
  `powershell_drivespace-273x300.png`, `RED_Alert-1.png`, plus
  `Query_Plan_Merge_Join.png`. The `<img>` tags were left in place, so these pages look
  exactly as they do today.
- **2 images were recovered** and now display again after years of being broken:
  `Boring_SCOM_Alert.png` and `EXCEPT-300x172.png`.
- **One dead link** to `/blog/` remains in the body of *Style over substance*.
- **"Protected: Consulting rates"** was password-protected. WordPress never sent its
  content to the browser, so it could not be captured — only the (now inert) password
  form. The post's content is not in this archive.

---

## Rebuilding the archive

`tools/` holds the scripts used to build this, in order. They only work while the
WordPress site is still online, so re-run them **before** decommissioning AWS if you
want a fresher capture.

They use paths relative to the current directory, so run them from a scratch directory
(not the repo root). They create `raw/` for the captured HTML and `site/` for the
finished output, which you then copy over this repo.

```bash
python3 -m pip install requests beautifulsoup4 lxml

python3 tools/crawl.py             # mirror all public HTML into raw/
python3 tools/assets.py            # download images, CSS, JS, fonts, avatars
python3 tools/css_assets.py        # assets referenced from inside CSS
python3 tools/build_search.py      # regenerate search-index.json
python3 tools/build_search_page.py # regenerate the /search/ page
python3 tools/build_hosting.py     # 404, feed, sitemaps, CNAME, robots
python3 tools/rewrite.py           # raw/ -> static site (run last)
python3 tools/check.py             # verify every local link resolves
```

`check.py` is the useful one: it walks every page and reports any local reference that
does not resolve to a file on disk. A clean run reports the 6 known-broken targets above
and nothing else.

To preview locally:

```bash
python3 -m http.server 8000
```
