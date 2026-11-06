"""Shared helpers for the lab-notes tools. Standard library only (Python 3.8+)."""
from __future__ import annotations

import html
import re
from datetime import date
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# --------------------------------------------------------------------------
# Folder layout:  <root>/YYYY/MM/YYYY-MM-DD/notes.md
# --------------------------------------------------------------------------
def day_dir(root: Path, d: date) -> Path:
    return root / f"{d:%Y}" / f"{d:%m}" / d.isoformat()


def iter_days(root: Path):
    """Return [(YYYY-MM-DD, day_path)] for every day folder that has notes.md, sorted."""
    out = []
    if not root.is_dir():
        return out
    for ydir in sorted(root.iterdir()):
        if not (ydir.is_dir() and re.fullmatch(r"\d{4}", ydir.name)):
            continue
        for mdir in sorted(ydir.iterdir()):
            if not (mdir.is_dir() and re.fullmatch(r"\d{2}", mdir.name)):
                continue
            for ddir in sorted(mdir.iterdir()):
                if ddir.is_dir() and DAY_RE.match(ddir.name) and (ddir / "notes.md").exists():
                    out.append((ddir.name, ddir))
    return out


# --------------------------------------------------------------------------
# Front matter (a tiny YAML subset: `key: value` and `key: [a, b]`)
# --------------------------------------------------------------------------
def split_frontmatter(text: str):
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip()
        if val.startswith("[") and val.endswith("]"):
            meta[key] = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
        else:
            meta[key] = val.strip("'\"")
    return meta, text[m.end():]


# --------------------------------------------------------------------------
# Scanning a note for open to-dos and inline #tags
# --------------------------------------------------------------------------
TASK_RE = re.compile(r"^(\s*[-*+]\s+)\[([ xX>])\]\s+(.*)$")
INLINE_TAG_RE = re.compile(r'(?<![\w&/#\[("=])#([A-Za-z][\w/-]*)')
FENCE_RE = re.compile(r"^\s*```")


def scan_note(text: str):
    """Return (todos, tags). todos = [(line_no, text)]. Skips code blocks and front matter."""
    todos, tags, in_code = [], set(), False
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                start = j + 1
                break
    for no, line in enumerate(lines[start:], start + 1):
        if FENCE_RE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = TASK_RE.match(line)
        if m:
            if m.group(2) == " " and m.group(3).strip():
                todos.append((no, m.group(3).strip()))
        elif re.search(r"(?<!\w)#todo\b", line, re.I):
            todos.append((no, re.sub(r"^\s*[-*+]\s+", "", line).strip()))
        stripped = re.sub(r"`[^`]*`", "", line)
        stripped = re.sub(r"\$[^$]*\$", "", stripped)
        for t in INLINE_TAG_RE.findall(stripped):
            if t.lower() != "todo":
                tags.add(t.lower())
    return todos, tags


def first_heading(body: str, default: str) -> str:
    in_code = False
    for line in body.splitlines():
        if FENCE_RE.match(line):
            in_code = not in_code
        if not in_code:
            m = re.match(r"^#\s+(.+?)\s*#*$", line)
            if m:
                return m.group(1)
    return default


# --------------------------------------------------------------------------
# Minimal Markdown -> HTML (headings, lists, task lists, tables, code, quotes,
# images, links, bold/italic, #tags, and $math$ passed through for KaTeX).
# --------------------------------------------------------------------------
def esc(s: str) -> str:
    return html.escape(s, quote=False)


def _attr(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).replace('"', "&quot;")


IMG_RE = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)')
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def inline(text: str) -> str:
    stash = []

    def keep(h):
        stash.append(h)
        return "\x00%d\x00" % (len(stash) - 1)

    text = re.sub(r"(`+)(.+?)\1", lambda m: keep("<code>%s</code>" % esc(m.group(2))), text)
    text = re.sub(r"\$\$(.+?)\$\$", lambda m: keep('<span class="math">$$%s$$</span>' % esc(m.group(1))), text)
    text = re.sub(
        r"(?<![\\$\w])\$(?![\s$])([^$\n]+?)(?<![\s\\])\$(?![\w$])",
        lambda m: keep('<span class="math">$%s$</span>' % esc(m.group(1))),
        text,
    )
    text = esc(text)
    text = INLINE_TAG_RE.sub(lambda m: '<span class="tag">#%s</span>' % m.group(1), text)

    def img(m):
        title = ' title="%s"' % _attr(m.group(3)) if m.group(3) else ""
        return keep('<img src="%s" alt="%s"%s loading="lazy">' % (m.group(2), _attr(m.group(1)), title))

    text = IMG_RE.sub(img, text)
    text = LINK_RE.sub(lambda m: keep('<a href="%s">' % m.group(2)) + m.group(1) + keep("</a>"), text)
    text = re.sub(r'(?<![">=\x00\w])(https?://[^\s<)\x00]+)', lambda m: keep('<a href="%s">%s</a>' % (m.group(1), m.group(1))), text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\*\w])\*(?![\s\*])(.+?)(?<![\s\*])\*(?![\*\w])", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_(?![\s_])(.+?)(?<![\s_])_(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", s).lower()).strip("-")


LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
HR_RE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _item(text: str):
    m = re.match(r"^\[([ xX>])\]\s+(.*)$", text, re.S)
    if m:
        st = m.group(1)
        if st == ">":
            box = '<span class="migrated" title="carried over">&rarr;</span> '
        else:
            box = '<input type="checkbox" disabled%s> ' % (" checked" if st in "xX" else "")
        return ' class="task"', box + inline(m.group(2))
    return "", inline(text)


def _render_list(items):
    out, stack = [], []
    for indent, ordered, text in items:
        tag = "ol" if ordered else "ul"
        if not stack or indent > stack[-1][0]:
            out.append("<%s>" % tag)
            stack.append((indent, tag))
        else:
            while len(stack) > 1 and indent < stack[-1][0]:
                out.append("</li></%s>" % stack.pop()[1])
            out.append("</li>")
        cls, body = _item(text)
        out.append("<li%s>%s" % (cls, body))
    while stack:
        out.append("</li></%s>" % stack.pop()[1])
    return "".join(out)


def _split_row(line: str):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", line)]


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out, para, i, n = [], [], 0, len(lines)

    def flush():
        if para:
            txt = "\n".join(s.strip() for s in para)
            im = IMG_RE.fullmatch(txt.strip())
            if im:
                out.append("<figure>%s<figcaption>%s</figcaption></figure>" % (
                    inline(txt.strip()), inline(im.group(3) or im.group(1))))
            else:
                out.append("<p>%s</p>" % inline(txt))
            para.clear()

    while i < n:
        line = lines[i]
        if not line.strip():
            flush(); i += 1; continue

        fm = re.match(r"^\s*```([\w+-]*)\s*$", line)
        if fm:
            flush(); buf = []; i += 1
            while i < n and not re.match(r"^\s*```\s*$", lines[i]):
                buf.append(lines[i]); i += 1
            i += 1
            out.append('<pre><code class="lang-%s">%s</code></pre>' % (fm.group(1), esc("\n".join(buf))))
            continue

        s = line.strip()
        if s.startswith("$$"):
            flush()
            if len(s) >= 4 and s.endswith("$$"):
                buf = [s[2:-2]]; i += 1
            else:
                buf = [s[2:]]; i += 1
                while i < n and "$$" not in lines[i]:
                    buf.append(lines[i]); i += 1
                if i < n:
                    buf.append(lines[i].split("$$")[0]); i += 1
            out.append('<div class="math-display">$$%s$$</div>' % esc("\n".join(buf).strip()))
            continue

        hm = HEAD_RE.match(line)
        if hm:
            flush()
            lvl, txt = len(hm.group(1)), inline(hm.group(2))
            out.append('<h%d id="%s">%s</h%d>' % (lvl, _slug(txt), txt, lvl))
            i += 1; continue

        if HR_RE.match(line):
            flush(); out.append("<hr>"); i += 1; continue

        if i + 1 < n and "|" in line and TABLE_SEP_RE.match(lines[i + 1]) and "-" in lines[i + 1]:
            flush()
            head = _split_row(line)
            aligns = []
            for c in _split_row(lines[i + 1]):
                aligns.append("center" if c.startswith(":") and c.endswith(":") else
                              "right" if c.endswith(":") else "left")
            i += 2; rows = []
            while i < n and lines[i].strip() and "|" in lines[i]:
                rows.append(_split_row(lines[i])); i += 1

            def cell(tag, c, k):
                al = aligns[k] if k < len(aligns) else "left"
                return '<%s style="text-align:%s">%s</%s>' % (tag, al, inline(c), tag)

            t = ["<table><thead><tr>"] + [cell("th", c, k) for k, c in enumerate(head)] + ["</tr></thead><tbody>"]
            for r in rows:
                t.append("<tr>" + "".join(cell("td", c, k) for k, c in enumerate(r)) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t)); continue

        if line.lstrip().startswith(">"):
            flush(); buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append("<blockquote>%s</blockquote>" % md_to_html("\n".join(buf)))
            continue

        lm = LIST_RE.match(line)
        if lm:
            flush(); items = []
            while i < n:
                l = lines[i]
                m2 = LIST_RE.match(l)
                if m2 and not HR_RE.match(l):
                    indent = len(m2.group(1).replace("\t", "    "))
                    items.append([indent, m2.group(2)[0].isdigit(), m2.group(3)]); i += 1
                elif not l.strip() and i + 1 < n and LIST_RE.match(lines[i + 1]):
                    i += 1
                elif l.strip() and l[0] in " \t" and items and not FENCE_RE.match(l):
                    items[-1][2] += "\n" + l.strip(); i += 1
                else:
                    break
            out.append(_render_list(items)); continue

        para.append(line); i += 1

    flush()
    return "\n".join(out)
