# johnmccormack.co.uk

Static WordPress snapshot; GitHub Pages serves the repo root, so pushing to
`main` deploys. Hand-editable HTML, no build step. Comment only non-obvious calls.

## Generated markup — never hand-edit a single page

`tools/darkmode.py`, `tools/banner.py` and `tools/menu.py` each rewrite every
root HTML page in place, so the dark-mode `<head>` tags, the notice banner and
the header menu are generated: change the script and re-run it. The first two
take `--revert`; `menu.py` has none. Everything else is safe to edit directly.

Only `--revert` and `--check` are parsed; any other flag applies the change.

The rest of `tools/` is the re-capture pipeline (`raw/` → `site/`) and never
touches the repo root. `tools/check.py` validates `site/`, so it will not catch
a broken link in what actually ships.

## CSS

- Route colours through the `--jm-*` properties in `assets/css/darkmode.css`. A
  new one needs its light value *and* both dark blocks (`[data-theme="dark"]`
  and `prefers-color-scheme: dark`), or dark mode breaks silently.
- The theme stylesheet (`wp-content/themes/modern-portfolio-pro/style.css`) often
  out-specifies you: it qualifies with the body class, so `.header-image
  .site-title a` beats `.site-title a` whatever the load order. Match its
  specificity rather than reaching for `!important`.
- It ships no `@media print` rules at all — print styling is per-page.
- Page-scoped CSS belongs in that page's own `<head>` (e.g. `jm-resume-css`).
