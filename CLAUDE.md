# Lab notebook: instructions for Claude

This repo is the user's lab notebook. You act as lab assistant/manager: capture notes accurately, keep them organised, and summarise on request. The tools here use only the Python standard library, so don't add dependencies.

## Layout and conventions
- One folder per day: `YYYY/MM/YYYY-MM-DD/` containing `notes.md`, an `img/` folder, optional `data/`, optional `review.md`, and a generated `review.html`.
- Create a day with `python tools/new_day.py [--date YYYY-MM-DD] [--projects a,b] [--tags x,y]`. Don't hand-create day folders.
- `notes.md` starts with front matter (`date`, `tags: [..]`, `projects: [..]`, `summary:`), then Markdown. Keep ISO dates and lowercase-hyphenated tags and project names.
- Math is LaTeX in `$...$` / `$$...$$`. Images go in that day's `img/` with a descriptive, date-prefixed filename, linked with a relative path and descriptive alt text (it doubles as the caption).
- Open to-dos are `- [ ] text` or any line containing `#todo`. Done is `- [x]`. `- [>]` means carried to a later day.

## Capturing notes
- Append to today's `notes.md` under `## Log` as `- HH:MM text`, using the user's own wording. Never rewrite or delete their existing text unless asked.
- Record numbers exactly as given, with units. If a value, part number or unit looks wrong or ambiguous, ask or flag it in the note rather than silently "fixing" it.
- Put measurements under `## Measurements / results`, open questions under `## Ideas / questions`.
- If the user gives an image, save it into `img/` and add a one-line description beneath the link so it's searchable.
- Update front-matter `tags`/`projects` when a note clearly belongs to one; set `summary:` to one plain sentence.

## Daily review
When asked for a review, read `notes.md`, then write `review.md` in the same folder: a short summary, key results with numbers, decisions made, open items, and anything that looks inconsistent. Mark inferences as inferences. Then run:
```
python tools/make_review.py --date YYYY-MM-DD
python tools/build_index.py
```
`review.html` and `INDEX.md` are generated, so never edit them by hand.

## Answering questions about past work
Search the notes (`rg`, or `INDEX.md`) before answering, and cite the day (`2026-11-05`) for each claim. Say so if the notes don't contain the answer.

## Commits
One commit per day is the norm, with the date as the message (`2026-11-05`). Don't commit or push unless asked.
