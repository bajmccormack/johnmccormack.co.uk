# johnmccormack.co.uk - static archive

A fully static snapshot of **John McCormack DBA** (previously hosted in WordPress), built
to be served from GitHub Pages so the EC2 + RDS + ELB stack can be shut down.

Captured from the live site on **8 August 2026**.

| | |
|---|---|
| HTML pages | 678 |
| Posts / pages | 105 / 2 |
| Categories / tags | 59 / 207 |
| Comments preserved | 56 (incl. trackbacks) |
| Images & other assets | ~590 |
| Total size | 116 MB |

---

## URLs are unchanged

Every original permalink still resolves, because each page is stored at its own path
(`/2019/03/put-tempdb-files-on-d-drive-in-azure-iaas/index.html`). Inbound links,
bookmarks and search-engine results keep working. `sitemap.xml` and `sitemap_index.xml`
are regenerated with the original `lastmod` values.

---

## What changed, and why

Appearance is unchanged - the rendered homepage is **pixel-identical** to the live site.
The differences are confined to things that cannot work without PHP and a database:

| Change | Reason |
|---|---|
| Comment form removed | Nothing can accept a POST. Existing comments still display in full. |
| Per-comment "Reply" links removed | They only existed to move the now-absent form. |
| Search rebuilt client-side | See below. |
| `wp-json`, `xmlrpc.php`, RSD, pingback and shortlink tags dropped | Dead endpoints. |
| RSS feed frozen at `/feed/index.xml` | A static snapshot; the old `/feed/` path no longer resolves. |
| Google Fonts + Gravatar avatars downloaded locally | Removes third-party runtime dependencies. |
| `johnmccormack.it` replaced by `.co.uk` throughout | That domain is dead and the paths are identical, so 61 previously-broken links now work. Visible link text and the `sameAs` entry in the page schema were updated to match. |

### Search

The search box works. URLs behave as before, so old search links still work.
