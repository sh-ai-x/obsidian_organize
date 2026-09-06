---
name: obsidian-organize:bootstrap
description: Set up an Obsidian vault with the topic-organizer directory layout (Clippings-processed, wiki, wiki-map) modeled after hermes-wiki-super. Use when initializing a new vault or migrating an existing one.
---

# obsidian-organize:bootstrap

## What it does

Creates the canonical directory layout that the rest of the obsidian-organize
plugin operates on. Modeled after `hermes-wiki-super`'s structure:

| Path | Purpose |
|---|---|
| `Clippings/processed/` | Archived raw clippings. `process-clippings` (upstream skill) drops files here once they've been triaged. |
| `Clippings/.keep` | Marker so the empty directory is preserved. |
| `wiki/` | Topic-organized wiki notes, one subdirectory per topic. Each subdirectory holds the canonical topic note (`README.md`) plus its supporting pages. |
| `wiki/<topic>/` | Topic subdirectory; the topic note lives at `wiki/<topic>/README.md` so the directory itself is the unit of organization. |
| `wiki-map.md` | Markdown index of all topics. One bullet per topic with a `[[wikilink]]` to the topic's `README.md`. The plugin's `add_wiki` skill appends a row here. |
| `_research/` | Staged research files (input to `add_wiki`). See `obsidian-organize:research`. |
| `_archive/research/` | Archive for retired research. See `obsidian-organize:remove_wiki`. |
| `topics/` | Alternative location for plugin-generated topic notes (skipped by default; see `references/layout.md`). |

## Invocation

```
/obsidian-organize:bootstrap <vault-path>
```

Optional flags:
- `--force` — overwrite existing files (default: refuse if any target exists).
- `--topics "alpha,beta,gamma"` — also seed empty `wiki/<topic>/` subdirectories
  for the named topics, each with an initial `README.md` containing the topic slug.

## Behavior

1. Resolve the vault root. If the path does not exist, create it.
2. For each top-level entry listed in `references/layout.md`, create the
   directory if missing (refuse on `--force` if it exists with content).
3. Write `wiki-map.md` if missing. The template contains:
   ```markdown
   ---
   type: wiki-map
   created: <ISO-8601>
   ---

   # Wiki Map

   <!-- obsidian-organize:wiki-map:auto-start -->
   <!-- Each row below is appended by obsidian-organize:add_wiki when a new topic lands. -->
   <!-- Do not edit by hand; re-running `bootstrap --force --topics ...` re-seeds. -->

   ## Topics

   <!-- obsidian-organize:wiki-map:auto-end -->
   ```
4. If `--topics` was supplied, create `wiki/<topic>/` for each name and seed
   `wiki/<topic>/README.md` with a minimal frontmatter (`topic` + `seeded-by`).
5. Print the resolved layout summary and exit 0.

## Edge cases

- Vault root exists but contains files the skill didn't create → fail with:
  "Refusing to bootstrap into a non-empty vault. Pass --force to overwrite,
  or move existing files out of the way."
- `wiki-map.md` already has rows between the auto-start / auto-end markers
  → leave them in place; only seed the empty template if the file is absent.
- The user has their own `wiki/` layout (e.g. subdirs with notes already
  in them) → refuse unless `--force` is set, to avoid clobbering.

## Reference vault (canonical example)

The plugin's reference vault is `~/Documents/Obsidian Vault/hermes-wiki-super/`.
New vaults bootstrapped with this skill mirror that structure so the same
upstream skills (`process-clippings`, `add-wiki`) work unmodified.

## See also

- `references/layout.md` — pinned directory tree + each path's contract.
- `obsidian-organize:research` — produces staged files in `_research/`.
- `obsidian-organize:add_wiki` — promotes staged research into a topic
  note at `topics/<topic>.md`. It does NOT touch `wiki-map.md` (that
  index is owned by `process_clippings`); see README.md:109 for the
  wiki/ vs topics/ separation.
- `obsidian-organize:remove_wiki` — archives `_research/<topic>.md` to
  `_archive/research/`. Like `add_wiki`, it does NOT touch `wiki-map.md`.
