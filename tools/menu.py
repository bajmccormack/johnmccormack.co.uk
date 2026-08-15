#!/usr/bin/env python3
"""Restructure the header menu across the static site.

The archive was captured from WordPress, so the menu markup is repeated in
every page. The only part that varies per page is the "you are here"
marking: current-* classes on <li> and aria-current="page" on <a>. This
script rewrites the structure and leaves that marking alone.

Changes applied:

  1. "Save money in Azure" is renamed to "Cost Optimization"
  2. "All posts" is renamed to "Posts"
  3. A "Resume" item is added, pointing at /resume/
  4. "Hire me" is moved to be the first sub-item under "Posts"
  5. The top level is put in the order given by ORDER below

It is idempotent: a page already carrying the new menu is left untouched,
so it is safe to re-run. There is no --revert; this edits site content
rather than adding a removable layer, so git is the way back.

    python3 tools/menu.py            # apply
    python3 tools/menu.py --check    # report only, change nothing
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "tools"}

NAV_RE = re.compile(r'<ul id="menu-menu"[^>]*>.*?</ul>(?=</nav>)', re.S)

AZURE_ID, POSTS_ID, HIRE_ID, PERSONAL_ID = "2339", "2900", "2192", "285"
RESUME_ID = "3000"

# Top level, in the order they should appear.
ORDER = [
    POSTS_ID,     # Posts
    RESUME_ID,    # Resume
    "1653",       # Free Training
    AZURE_ID,     # Cost Optimization
    PERSONAL_ID,  # Personal
]

RESUME_ITEM = (
    f'<li id="menu-item-{RESUME_ID}" class="menu-item menu-item-type-post_type '
    f'menu-item-object-page menu-item-{RESUME_ID}">'
    f'<a href="/resume/"><span >Resume</span></a></li>'
)

stats = {"pages": 0, "changed": 0, "already": 0, "no_menu": 0}


def html_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and d != "embed"]
        for fn in filenames:
            if fn.endswith(".html"):
                yield os.path.join(dirpath, fn)


def find_item(nav, item_id):
    """Return (start, end) of the <li> for a menu item, nesting included."""
    m = re.search(rf'<li id="menu-item-{item_id}"[^>]*>', nav)
    if not m:
        return None
    depth, i = 0, m.start()
    for tag in re.finditer(r'<li\b[^>]*>|</li>', nav[m.start():]):
        depth += 1 if tag.group(0).startswith('<li') else -1
        if depth == 0:
            return m.start(), m.start() + tag.end()
    return None


def rename(nav, item_id, new_label):
    """Replace the label of one item, leaving its href and classes alone."""
    span = re.compile(
        rf'(<li id="menu-item-{item_id}"[^>]*>\s*<a\b[^>]*>\s*<span[^>]*>)(.*?)(</span>)',
        re.S)
    return span.sub(lambda m: m.group(1) + new_label + m.group(3), nav, count=1)


def top_level(nav):
    """Split the menu <ul> into its direct children.

    Returns (end of the <ul> tag, [(id, separator before it, html)],
    whatever trailing text sits before </ul>). The separators are kept so
    the markup's own line breaks survive a reorder.
    """
    open_tag = re.match(r'<ul id="menu-menu"[^>]*>', nav).end()
    body = nav[open_tag:]
    assert body.endswith('</ul>')
    body = body[:-len('</ul>')]

    items, depth, start, item_id, pos = [], 0, None, None, 0
    for tag in re.finditer(r'<li id="(menu-item-\d+)"[^>]*>|<li\b[^>]*>|</li>',
                           body):
        opening = not tag.group(0).startswith('</')
        if opening and depth == 0:
            start, item_id = tag.start(), tag.group(1)
        depth += 1 if opening else -1
        if depth == 0 and start is not None:
            items.append((item_id[len("menu-item-"):],
                          body[pos:start], body[start:tag.end()]))
            pos, start = tag.end(), None
    return open_tag, items, body[pos:]


def reorder(nav):
    open_tag, items, trailing = top_level(nav)
    by_id = {i: h for i, _, h in items}
    seps = [s for _, s, _ in items]

    # Only reorder a menu that is exactly the set we expect, and only when
    # nothing but whitespace separates the items. Anything else is left
    # alone rather than silently rearranged or dropped.
    if sorted(by_id) != sorted(ORDER) or len(items) != len(ORDER):
        return nav
    if any(s.strip() for s in seps) or trailing.strip():
        return nav

    # Separators stay in their original slots, so the line breaks land in
    # the same places regardless of which item moved where.
    body = ''.join(seps[n] + by_id[i] for n, i in enumerate(ORDER))
    return nav[:open_tag] + body + trailing + '</ul>'


def rewrite(nav):
    # 1 + 2. Labels.
    nav = rename(nav, AZURE_ID, "Cost Optimization")
    nav = rename(nav, POSTS_ID, "Posts")

    # 4. Lift "Hire me" out and drop it in as the first child of "Posts".
    #    Done before the insert so the offsets stay simple.
    span = find_item(nav, HIRE_ID)
    if span:
        hire = nav[span[0]:span[1]]
        nav = nav[:span[0]] + nav[span[1]:]

        posts = find_item(nav, POSTS_ID)
        block = nav[posts[0]:posts[1]]
        anchor = '<ul class="sub-menu">'
        at = block.index(anchor) + len(anchor)
        block = block[:at] + hire + block[at:]
        nav = nav[:posts[0]] + block + nav[posts[1]:]

    # 3. Resume, straight after "Personal".
    if f'menu-item-{RESUME_ID}"' not in nav:
        personal = find_item(nav, PERSONAL_ID)
        nav = nav[:personal[1]] + RESUME_ITEM + nav[personal[1]:]

    # 5. Put the top level in the order we want.
    return reorder(nav)


def mark_current(nav, path):
    """Give the resume page's own menu item the marking WordPress would."""
    if os.path.basename(os.path.dirname(path)) != "resume":
        return nav
    tag = re.search(rf'<li id="menu-item-{RESUME_ID}"[^>]*>', nav)
    if tag and 'current-menu-item' in tag.group(0):
        return nav
    return re.sub(
        rf'(<li id="menu-item-{RESUME_ID}" class="menu-item)([^"]*")(><a href="/resume/")',
        r'\1 current-menu-item page_item current_page_item\2\3 aria-current="page"',
        nav, count=1)


def process(text, path):
    original = text
    m = NAV_RE.search(text)
    if not m:
        stats["no_menu"] += 1
        return text, False
    nav = m.group(0)

    # Recompute the menu and compare, rather than testing for a marker.
    # That way a change to ORDER or a label is picked up on the next run.
    new = mark_current(rewrite(nav), path)
    text = text[:m.start()] + new + text[m.end():]

    if text == original:
        stats["already"] += 1
        return text, False
    stats["changed"] += 1
    return text, True


def main():
    check = "--check" in sys.argv
    for path in html_files():
        stats["pages"] += 1
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        new, changed = process(text, path)
        if changed and not check:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)

    print(("would change: " if check else "applied: ") +
          f"{stats['changed']} of {stats['pages']} pages scanned")
    print(f"  menu rewritten  : {stats['changed']}")
    print(f"  already correct : {stats['already']}")
    print(f"  no menu found   : {stats['no_menu']}")


if __name__ == "__main__":
    main()
