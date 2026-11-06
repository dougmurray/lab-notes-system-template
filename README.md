# lab-notes-system-template

A plain-text lab notebook that is searchable, supports math and pictures, versions with Git, and works well with Claude as a lab assistant. Notes are Markdown; a small standard-library Python toolkit creates each day's folder, builds a browsable `review.html`, and keeps a searchable `INDEX.md`.

**Design rules:** plain text wins (it greps and diffs), pictures sit next to the note that uses them, structure lives in front matter and tags rather than in the folder tree, and generated files are never edited by hand.

## Layout

```
lab-notes/
├── 2026/
│   └── 11/
│       └── 2026-11-05/
│           ├── notes.md        # you write this (or Claude, from your dictation)
│           ├── review.md       # optional: Claude's summary/commentary for the day
│           ├── review.html     # generated: notes + review + open items + images
│           ├── img/            # screenshots, photos, plots for this day
│           └── data/           # small CSV/JSON you reference (large raw data stays out)
├── projects/                   # evergreen, distilled notes per project (optional)
├── templates/daily.md          # what a new day starts from
├── tools/                      # new_day.py, make_review.py, build_index.py (stdlib only)
├── examples/sample-lab/        # fictional demo vault. Delete in your own copy
├── INDEX.md                    # generated: open to-dos, by project, by tag, all days
└── CLAUDE.md                   # conventions for Claude working in this repo
```

Year/month/day keeps every directory small (~20 entries). ISO names (`2026-11-05`) sort correctly everywhere, including `git log` and search results.

## Daily workflow

```bash
python tools/new_day.py --projects adc-acquisition --tags noise    # create today's note
# ...take notes in notes.md all day, drop images in img/ ...
python tools/make_review.py                                        # build review.html
python tools/build_index.py                                        # refresh INDEX.md
git add -A && git commit -m "2026-11-05"
```

- `new_day.py` carries open `- [ ]` items from the previous day into the new note and marks the old ones `- [>]` (carried), so every open item lives in one place. Use `--no-carry` to skip, `--date YYYY-MM-DD` for another day.
- `make_review.py --all` rebuilds every day. If a day has a `review.md`, it is rendered at the top as "Review".
- Try it on the demo: `python tools/make_review.py --root examples/sample-lab --all` then open `examples/sample-lab/2026/01/2026-01-15/review.html`.

## Note format

Front matter, then Markdown:

```markdown
---
date: 2026-11-05
tags: [adc, noise]
projects: [adc-acquisition]
summary: One line that shows up in INDEX.md
---

# 2026-11-05 (Thursday)

## Log
- 09:10 Measured shorted-input noise at 10 SPS. #noise
- [ ] Re-run with the buffer bypassed          <- open to-do (also: any line with #todo)

$$e_n = \sqrt{4 k T R \,\Delta f}$$              <- display math; inline is $R = 10\,\mathrm{k\Omega}$

![Bode plot of the loop gain](img/2026-11-05-bode-loop-gain.png)
```

- **Math:** `$...$` inline, `$$...$$` display (LaTeX, rendered by KaTeX in `review.html`; also renders in VS Code, GitHub and Obsidian).
- **Pictures:** descriptive filenames and a caption in the alt text. Search can't see inside an image, so the words around it are what make it findable.
- **Tags:** front-matter `tags:` plus inline `#tags`. **Projects:** front-matter `projects:`.

## Searching

```bash
rg -i "1/f corner"                    # full text across every day
rg "^tags:.*noise" -g notes.md        # days tagged noise
rg "\[ \]" -g notes.md                # every open to-do
rg -l "ad7175" --sort path            # which days mention a part, in date order
git log --oneline -- 2026/11          # a month's commits
```

`INDEX.md` gives the same views pre-built (open to-dos, by project, by tag).

## Using it with Claude

`CLAUDE.md` tells Claude the conventions (where today's note is, how to append timestamped log lines, how to write `review.md`). Typical prompts:

- "Log: measured 12.8 nV/rtHz at 1 kHz with inputs shorted. Tag it noise."
- "Add this screenshot to today's notes as the loop-gain plot." (attach image)
- "Write today's review.md, then rebuild review.html and INDEX.md."
- "What did I conclude about the reference buffer noise last month?"

## Math rendering offline (important for locked-down networks)

By default `review.html` loads KaTeX from the jsDelivr CDN. If that's blocked, vendor KaTeX once and the pages will use it automatically:

1. Download the KaTeX release (`katex.tar.gz`, 0.16.x) on a machine where that's allowed.
2. Copy `katex.min.js`, `katex.min.css`, the `fonts/` folder and `contrib/auto-render.min.js` into `tools/vendor/katex/` (keeping the `contrib/` and `fonts/` subfolders).
3. Re-run `make_review.py --all`.

Without KaTeX the page still works; equations just show as raw LaTeX.

## Setting it up on another machine

1. Use this repo as a template (GitHub: "Use this template") or copy the files into a new repo.
2. Delete `examples/` (it's fictional demo data).
3. Needs only Python 3.8+ and Git. The tools use the standard library, make no network calls, and have no dependencies.
4. Optional: install [ripgrep](https://github.com/BurntSushi/ripgrep) for fast search; enable Git LFS for large images by uncommenting the lines in `.gitattributes`.
5. Keep raw captures and big datasets out of the repo (`**/raw/` is git-ignored). Commit the figure you reference.

## Ideas for later

Weekly roll-up generated from the dailies; a `projects/<name>.md` file where conclusions get distilled from the dailies; a pre-commit hook that runs `build_index.py`.
