#!/usr/bin/env python3
"""Build review.html for a day (self-contained page: rendered notes, open items, attachments).

  python tools/make_review.py                    # today
  python tools/make_review.py --date 2026-11-05
  python tools/make_review.py --all              # rebuild every day

If the day folder contains review.md (e.g. a summary written by Claude), it is
rendered at the top under "Review". Math ($...$ and $$...$$) is rendered by KaTeX:
the page uses tools/vendor/katex/ if present, otherwise the jsDelivr CDN.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from labnotes import (REPO_ROOT, TOOLS_DIR, day_dir, esc, first_heading, iter_days,  # noqa: E402
                      md_to_html, scan_note, split_frontmatter)

IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".tif", ".tiff"}
SKIP = {"notes.md", "review.md", "review.html"}
KATEX_VERSION = "0.16.11"

CSS = """
:root{--bg:#fbfbfa;--fg:#1c1d1f;--muted:#6b6f76;--line:#e2e3e5;--card:#fff;--accent:#2457c5;--chip:#e9eefb;--code:#f3f4f6}
@media (prefers-color-scheme:dark){:root{--bg:#141517;--fg:#e6e7e9;--muted:#9a9ea6;--line:#2c2e33;--card:#1b1c1f;--accent:#7aa2f7;--chip:#232a3d;--code:#222428}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 16px 80px}
h1,h2,h3{line-height:1.25} h1{font-size:1.8rem;margin:.2em 0} h2{font-size:1.25rem;margin-top:2em;border-bottom:1px solid var(--line);padding-bottom:.25em}
.meta{color:var(--muted);font-size:.9rem;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.chip,.tag{background:var(--chip);color:var(--accent);border-radius:99px;padding:1px 9px;font-size:.85rem}
.tag{padding:0 6px;border-radius:4px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:4px 16px;margin:16px 0}
.card.open{border-left:4px solid var(--accent)}
p{white-space:pre-line;margin:.7em 0}
a{color:var(--accent)} code{background:var(--code);padding:1px 5px;border-radius:4px;font-size:.9em}
pre{background:var(--code);padding:12px;border-radius:8px;overflow:auto} pre code{padding:0;background:none}
table{border-collapse:collapse;margin:1em 0;max-width:100%;display:block;overflow-x:auto} th,td{border:1px solid var(--line);padding:5px 10px} th{background:var(--code)}
blockquote{margin:1em 0;padding:0 14px;border-left:3px solid var(--line);color:var(--muted)}
img{max-width:100%;height:auto;border-radius:6px} figure{margin:1em 0} figcaption{color:var(--muted);font-size:.88rem;margin-top:4px}
ul,ol{padding-left:1.5em} li.task{list-style:none;margin-left:-1.2em} li.task input{margin-right:6px} .migrated{color:var(--muted)}
.math-display{overflow-x:auto;margin:1em 0}
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;margin:12px 0}
.gallery figure{margin:0}
footer{margin-top:3em;color:var(--muted);font-size:.8rem}
@media print{body{background:#fff;color:#000}main{padding:0}.card{break-inside:avoid}}
"""


def katex_head(day_path: Path) -> str:
    local = TOOLS_DIR / "vendor" / "katex"
    if (local / "katex.min.js").exists():
        base = os.path.relpath(local, day_path).replace(os.sep, "/")
    else:
        base = "https://cdn.jsdelivr.net/npm/katex@%s/dist" % KATEX_VERSION
    return (
        '<link rel="stylesheet" href="%(b)s/katex.min.css">\n'
        '<script defer src="%(b)s/katex.min.js"></script>\n'
        '<script defer src="%(b)s/contrib/auto-render.min.js" onload="renderMathInElement(document.body,'
        "{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]})\"></script>"
    ) % {"b": base}


def attachments(day_path: Path):
    imgs, files = [], []
    for p in sorted(day_path.rglob("*")):
        if not p.is_file() or p.name.startswith(".") or p.parent == day_path and p.name in SKIP:
            continue
        rel = p.relative_to(day_path).as_posix()
        (imgs if p.suffix.lower() in IMG_EXT else files).append(rel)
    return imgs, files


def build(day_path: Path) -> Path:
    day = day_path.name
    text = (day_path / "notes.md").read_text(encoding="utf-8")
    meta, body = split_frontmatter(text)
    todos, _ = scan_note(text)
    title = first_heading(body, day)

    chips = "".join('<span class="chip">%s</span>' % esc(t) for t in meta.get("tags", []) or [])
    projects = "".join('<span class="chip">%s</span>' % esc(t) for t in meta.get("projects", []) or [])
    parts = ['<h1>%s</h1>' % esc(title)]
    parts.append('<div class="meta"><span>%s</span>%s%s</div>' % (
        esc(meta.get("date", day)),
        (" &middot; projects: " + projects) if projects else "",
        (" &middot; tags: " + chips) if chips else ""))
    if meta.get("summary"):
        parts.append('<p><em>%s</em></p>' % esc(meta["summary"]))

    review = day_path / "review.md"
    if review.exists():
        parts.append('<h2>Review</h2><div class="card">%s</div>' % md_to_html(review.read_text(encoding="utf-8")))

    if todos:
        li = "".join("<li class=\"task\"><input type=\"checkbox\" disabled> %s</li>" % esc(t) for _, t in todos)
        parts.append('<h2>Open items</h2><div class="card open"><ul>%s</ul></div>' % li)

    # Drop the leading H1 from the body; it's already the page title.
    body_html = md_to_html(body)
    if body_html.startswith("<h1"):
        body_html = body_html.split("</h1>", 1)[1]
    parts.append('<h2>Notes</h2>' + body_html)

    imgs, files = attachments(day_path)
    if imgs:
        figs = "".join('<figure><a href="%s"><img src="%s" loading="lazy"></a><figcaption>%s</figcaption></figure>'
                       % (esc(i), esc(i), esc(i)) for i in imgs)
        parts.append('<h2>Images</h2><div class="gallery">%s</div>' % figs)
    if files:
        parts.append('<h2>Files</h2><ul>%s</ul>' % "".join('<li><a href="%s">%s</a></li>' % (esc(f), esc(f)) for f in files))

    page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s</title>
<style>%(css)s</style>
%(katex)s
</head><body><main>
%(content)s
<footer>Generated from notes.md by tools/make_review.py &mdash; edit the notes, not this file.</footer>
</main></body></html>
""" % {"title": esc("%s — %s" % (day, title) if day not in title else title), "css": CSS,
       "katex": katex_head(day_path), "content": "\n".join(parts)}
    out = day_path / "review.html"
    out.write_text(page, encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--root", type=Path, default=REPO_ROOT)
    ap.add_argument("--all", action="store_true", help="rebuild every day")
    args = ap.parse_args()

    if args.all:
        days = [p for _, p in iter_days(args.root)]
    else:
        d = date.fromisoformat(args.date) if args.date else date.today()
        p = day_dir(args.root, d)
        if not (p / "notes.md").exists():
            print("No notes.md for %s (looked in %s)" % (d, p), file=sys.stderr)
            return 1
        days = [p]
    for p in days:
        print("Wrote %s" % build(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
