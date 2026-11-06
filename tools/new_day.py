#!/usr/bin/env python3
"""Create today's note folder from templates/daily.md.

  python tools/new_day.py                      # today
  python tools/new_day.py --date 2026-11-06    # a specific day
  python tools/new_day.py --projects adc-acquisition --tags noise,adc
  python tools/new_day.py --no-carry           # don't migrate open to-dos

Open to-dos (`- [ ]`) from the most recent earlier day are copied into the new
note and marked `- [>]` (carried over) in the old one, so each open item lives
in exactly one place.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from labnotes import REPO_ROOT, TASK_RE, FENCE_RE, day_dir, iter_days  # noqa: E402


def fmt_list(csv: str) -> str:
    items = [x.strip() for x in csv.split(",") if x.strip()]
    return "[" + ", ".join(items) + "]"


def carry_over(root: Path, target: str):
    """Move open tasks from the latest earlier day. Returns (lines, source_day)."""
    earlier = [(d, p) for d, p in iter_days(root) if d < target]
    if not earlier:
        return [], None
    src_day, src_path = earlier[-1]
    note = src_path / "notes.md"
    lines = note.read_text(encoding="utf-8").splitlines()
    carried, in_code, changed = [], False, False
    for k, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_code = not in_code
            continue
        m = TASK_RE.match(line)
        if m and not in_code and m.group(2) == " ":
            carried.append("- [ ] " + m.group(3).strip())
            lines[k] = "%s[>] %s (carried to %s)" % (m.group(1), m.group(3).strip(), target)
            changed = True
    if changed:
        note.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return carried, src_day


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--root", type=Path, default=REPO_ROOT, help="notes root (default: repo root)")
    ap.add_argument("--tags", default="", help="comma-separated tags for the front matter")
    ap.add_argument("--projects", default="", help="comma-separated projects for the front matter")
    ap.add_argument("--no-carry", action="store_true", help="don't carry over open to-dos")
    args = ap.parse_args()

    d = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    folder = day_dir(args.root, d)
    note = folder / "notes.md"
    if note.exists():
        print("Already exists: %s" % note)
        return 0

    carried, src = ([], None) if args.no_carry else carry_over(args.root, d.isoformat())
    template = (args.root / "templates" / "daily.md")
    if not template.exists():
        template = REPO_ROOT / "templates" / "daily.md"
    text = template.read_text(encoding="utf-8")
    text = (text.replace("{{date}}", d.isoformat())
                .replace("{{weekday}}", d.strftime("%A"))
                .replace("{{tags}}", fmt_list(args.tags))
                .replace("{{projects}}", fmt_list(args.projects))
                .replace("{{carryover}}", "\n".join(carried) if carried else "- [ ] "))

    (folder / "img").mkdir(parents=True, exist_ok=True)
    (folder / "img" / ".gitkeep").touch()
    note.write_text(text, encoding="utf-8")
    print("Created %s" % note)
    if carried:
        print("Carried %d open to-do(s) over from %s" % (len(carried), src))
    return 0


if __name__ == "__main__":
    sys.exit(main())
