---
name: obsidian-organize:process_clippings
description: Scan Clippings/ for unprocessed files and create LLM-Wiki topic entries under wiki/. Use after a batch of clippings lands in <vault>/Clippings/ (e.g. from a research-agent run).
---

# obsidian-organize:process_clippings

## What it does

Walks `<vault>/Clippings/` (top-level only — `Clippings/processed/` is
always excluded) and for every `.md` file there:

1. Derives a **topic slug** from the file's first `# H1` heading
   (fallback: filename stem).
2. Creates `wiki/<topic>/README.md` — the LLM-Wiki topic hub, in the
   format modeled on `hermes-wiki-super` (see `references/wiki-format.md`).
3. Writes `wiki/<topic>/clippings/<safe-filename>.md` with a
   `type: clipping` frontmatter envelope + the original body verbatim.
4. Moves the source to `Clippings/processed/<safe-filename>.md`,
   disambiguating with an ISO-8601 suffix if the target already exists.
5. Appends a row to `wiki-map.md` between the auto-start / auto-end
   markers (or seeds the file with the template if it doesn't exist yet).

The skill is **additive** — it sits between the upstream
`hermes-wiki-super/process-clippings` skill (or whatever tool drops
files into `Clippings/`) and the existing `obsidian-organize:add_wiki`
flow. `process_clippings` is the deterministic layer; the LLM in this
skill only writes the topic-README `> description` line, if asked.

## Invocation

```
/obsidian-organize:process_clippings [<vault-path>]
```

Optional flags:
- `--dry-run` — print the plan (per-clipping topic + target paths),
  do not write or move anything.
- `--include-processed` — also re-process files in `Clippings/processed/`
  (default: skip them). Useful after a manual restore.
- `--topic-override <slug>` — force every clipping in this run to land
  under the named topic (rare; default is per-clipping H1 / filename).
- `--no-wiki-map` — skip the `wiki-map.md` row append (useful when the
  vault uses a different index format).

The vault root resolves from `OBSIDIAN_VAULT` (env) or `--vault <path>`
and the skill fails with a clear message if neither is set.

## Behavior

1. Resolve the vault root. If `Clippings/` does not exist, exit 0 with
   `nothing to process`.
2. Snapshot `.md` files at the top level of `Clippings/`, sorted by
   name. Skip `processed/`, `*.keep`, dotfiles.
3. For each candidate:
   1. `extract_topic_slug(text, filename)` → topic
   2. Ensure `wiki/<topic>/` and `wiki/<topic>/clippings/` exist.
   3. If `wiki/<topic>/README.md` is missing, write the LLM-Wiki
      template (`render_topic_readme`).
   4. Render the per-clipping page via `render_clipping_page`
      (frontmatter envelope + body).
   5. Compute the destination in `Clippings/processed/` via
      `unique_processed_path`; rename the source into it.
   6. Append a row to `wiki-map.md` (`_append_wiki_map_row`).
4. Print a summary: how many clippings processed, the per-clipping
   `(topic, source, moved_to)` triple, and any skipped files.

## Topic resolution

`extract_topic_slug` is the single source of truth:

- Walks the body line-by-line, takes the first line that starts with
  `# `, lowercases + slug-strips it.
- If that produces an empty slug (e.g. the heading was pure non-ASCII),
  falls back to the filename stem with the same normalization.
- If that still produces an empty slug, replaces whitespace and
  underscores with hyphens but otherwise preserves the original
  characters (so Korean / CJK headings survive as topic directory
  names, since most modern filesystems handle Unicode).

See `skills/_lib/slug.py:normalize_topic_slug` for the strict-ASCII
slug rules used by the rest of the plugin. `process_clippings` is the
one place that permits non-ASCII topic slugs.

## Edge cases

- `Clippings/` doesn't exist → exit 0 (no-op).
- `Clippings/` is empty → exit 0 (no-op).
- Clipping has no H1 → fall back to filename stem.
- Two clippings on the same topic → both land under `wiki/<topic>/clippings/`
  with their original filenames preserved; the topic README is created
  once.
- Two clippings on different topics → each gets its own `wiki/<topic>/`.
- Source filename collides with an existing file in
  `Clippings/processed/` → renamed with an ISO-8601 suffix
  (`a.md` → `a-20260905T120000Z.md`).
- `wiki-map.md` doesn't exist → seeded with the LLM-Wiki template,
  then the new row is appended.
- `wiki-map.md` exists but lacks the auto-end marker → row appended at
  the bottom.
- Vault root unset → fail with: "Set OBSIDIAN_VAULT or pass --vault <path>".
- `--dry-run` → no writes, no renames, no `wiki-map.md` edits; the
  summary still prints what *would* have happened.

## Reference

- `references/wiki-format.md` — the LLM-Wiki topic-README template,
  frontmatter for per-clipping pages, and the `wiki-map.md` block
  the skill seeds.
- `skills/_lib/process_clippings.py` — the deterministic helpers
  (`process_clippings`, `extract_topic_slug`, `render_topic_readme`,
  `render_clipping_page`, `resolve_*`, `unique_processed_path`).
- `hermes-wiki-super` — the vault convention this skill mirrors.
- `obsidian-organize:add_wiki` — promotes staged research files into
  topic notes (different pipeline; same `wiki/<topic>/README.md` shape).
- `obsidian-organize:remove_wiki` — retires a topic note (removes
  the `wiki-map.md` row added by this skill).