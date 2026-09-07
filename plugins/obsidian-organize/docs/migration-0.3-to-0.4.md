# Migration 0.3 → 0.4

The 0.4 release moved `process_clippings` and `add_wiki` from a flat
`topics/<topic>.md` model to a hermes-wiki-super LLM-Wiki layout.
Existing 0.3.x notes need a one-time migration before the new layout
will render correctly in Obsidian's graph view.

## What changes

| 0.3.x | 0.4 |
|---|---|
| `topics/<topic>.md` | `wiki/<domain>/<filename>.md` |
| `wiki/<topic>/README.md` (per-topic hub) | domain `index.md` / `<hub>.md` |
| `tags: [topic/<topic>]` (hierarchical) | `tags: [kebab-case, keywords, ...]` (flat) |
| `status: active` in topic note | `status:` removed; leaf notes have no lifecycle field |
| No `## Related` body section | `## Related` with `[[wikilinks]]` is mandatory |
| `wiki-map.md` auto-marker block + `## Topics` table | Grouped sections (e.g. `## 🤖 AI Dev Tools`) with `[[wikilinks]]` bullets |

## Why the migration is needed

The 0.3.x output had two properties that broke Obsidian's graph view:

1. Hierarchical tags like `topic/<topic>` did not connect to any other
   note, so the graph showed each note as an isolated dot.
2. `## Related` did not exist, so there were no `[[wikilinks]]` between
   notes.

The 0.4 layout fixes both: flat tags overlap between notes (so the
graph connects), and `## Related` is mandatory (so the local graph
spider is explicit).

## Per-note migration

For each `topics/<topic>.md` in the vault:

1. Read the frontmatter. Note the `tags:` list, the `sources:` list,
   and any cross-references in the body.
2. Route the topic via `skills/_shared/wiki-router.md` to pick the
   destination `wiki/<domain>/`.
3. Pick a new filename. If the destination domain uses numbered pages
   (`00-…`, `01-…`), continue the sequence; otherwise use a
   content-derived kebab-case name.
4. Distill the body into a leaf note per
   `skills/_shared/note-schema.md`: TL;DR blockquote, sections, and a
   `## Related` section whose bullets use `[[wikilinks]]` to point at
   the same notes the old topic's `## Related` referenced (when those
   exist in the new layout).
5. Replace the old `tags: [topic/<topic>]` with 3–7 flat keywords
   drawn from the body and from tags already in use in the target
   domain.
6. Add a `related:` frontmatter list of 2–5 vault-relative paths.
7. Append a log entry to `wiki/<domain>/log.md`.
8. Add a `[[wikilink]]` to the new note in the root `wiki-map.md`,
   inside the section for the target domain.
9. Delete the old `topics/<topic>.md`.

## Per-vault migration

Run the steps above for every `topics/<topic>.md` in the vault. Order
does not matter — each migration is independent. The end state:

- `topics/` is empty (then deletable).
- Each `wiki/<domain>/` has the notes routed into it, an `index.md`
  (or `<hub>.md`), and a `log.md`.
- `wiki-map.md` is in the new grouped shape with `[[wikilinks]]`
  bullets.

## When you can skip it

If your vault is brand new and was bootstrapped with 0.4, no
migration is needed. The 0.4 layout is the only one that ships from
this version onward.

## Tooling status

A `migrate-vault.py` script is not yet part of this release. The
migration is currently a manual or LLM-driven pass that follows the
per-note steps above. A scripted migration is a follow-up.
