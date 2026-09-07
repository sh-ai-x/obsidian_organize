# obsidian-organize

A Claude Code plugin that organizes an Obsidian vault in the
`hermes-wiki-super` LLM-Wiki style.

## Skills

| Skill ID | Purpose |
|---|---|
| `obsidian-organize:bootstrap` | Create the canonical vault layout (Clippings/, wiki/, _research/, _archive/, wiki-map.md). |
| `obsidian-organize:process_clippings` | Distill raw Clippings/ files into Karpathy-style leaf notes under the right `wiki/<domain>/`. Archive originals. |
| `obsidian-organize:research` | Stage source material on a topic into `_research/<topic>.md` using the LLM-Wiki frontmatter shape. |
| `obsidian-organize:add_wiki` | Write a new leaf note from a topic, free text, or staged file. Routes via the shared wiki-router. |
| `obsidian-organize:remove_wiki` | Retire a leaf note and clean up the back-links. |

## Layout

```
plugins/obsidian-organize/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── _shared/                  # shared references for the LLM-driven flow
│   │   ├── note-schema.md        # canonical leaf-note frontmatter + body
│   │   └── wiki-router.md        # which wiki/<domain>/ a topic belongs in
│   ├── _lib/                     # LEGACY (0.3.x) — see "0.3 → 0.4 migration" below
│   ├── bootstrap/                # NOT YET MIGRATED — still seeds 0.3.x layout
│   │   ├── SKILL.md
│   │   └── references/layout.md
│   ├── process_clippings/        # 0.4 (LLM-driven, hermes-style)
│   │   └── SKILL.md
│   ├── research/                 # 0.4 (hermes-style frontmatter)
│   │   ├── SKILL.md
│   │   └── references/output-schema.md
│   ├── add_wiki/                 # 0.4 (LLM-driven, hermes-style)
│   │   └── SKILL.md
│   └── remove_wiki/              # NOT YET MIGRATED — targets 0.3.x topics/
│       ├── SKILL.md
│       └── references/cleanup-rules.md
├── tests/                        # LEGACY (0.3.x) — exercises _lib/ deterministic flow
├── docs/
│   └── migration-0.3-to-0.4.md
└── README.md
```

## Vault conventions inherited from hermes-wiki-super

The 0.4 redesign mirrors `hermes-wiki-super` directly. Leaf notes
land under `wiki/<domain>/` (one folder per knowledge area), each with
flat keyword tags, an explicit `related:` list, a TL;DR blockquote, and
a `## Related` section whose `[[wikilinks]]` drive Obsidian's graph
view. See `skills/_shared/note-schema.md` for the full shape and
`skills/_shared/wiki-router.md` for routing rules.

The plugin is **additive** — it does not replace
`hermes-wiki-super/add-wiki` or `hermes-wiki-super/process-clippings`.
It is the formal, version-pinned version of the same convention.

- `_research/<topic>.md` is the staged input (frontmatter in the
  LLM-Wiki shape) produced by `obsidian-organize:research`.
- `wiki/<domain>/<filename>.md` is the leaf note produced by
  `obsidian-organize:process_clippings` (input: a Clippings/ file) or
  `obsidian-organize:add_wiki` (input: a topic, free text, or staged
  file).
- `wiki-map.md` at the vault root is the master index, with bullets
  grouped by domain.
- `wiki/<domain>/log.md` is the per-domain change log, appended on
  every ingest.
- `Clippings/processed/` is the archive of originals after
  `process_clippings` finishes.
- `obsidian-organize:remove_wiki` retires a leaf note and cleans up
  the `## Related` back-links in sibling notes.

## 0.3 → 0.4 migration

0.3.x produced `topics/<topic>.md` notes with hierarchical
`topic/<topic>` tags and no Obsidian graph edges. 0.4 produces
`wiki/<domain>/<filename>.md` notes with flat keyword tags and a
`## Related` section that lights up the graph. Existing 0.3.x notes
need a one-time migration before the new layout will render
correctly in Obsidian — see
[`docs/migration-0.3-to-0.4.md`](docs/migration-0.3-to-0.4.md) for
the per-note steps.

### Status of the legacy 0.3.x code paths

- **`skills/_lib/`** — kept for the 0.3.x pytest suite. No new
  functionality. Removal is a follow-up that runs the red-first
  removal cycle.
- **`skills/bootstrap/SKILL.md` and `references/layout.md`** — still
  describe the 0.3.x flat layout (`topics/`, `wiki/<topic>/README.md`
  per topic, `## Topics` rows in `wiki-map.md`). Running
  `bootstrap` then `process_clippings` / `add_wiki` on the same vault
  produces two incompatible layouts. The fix is to update
  `bootstrap` for 0.4 in a follow-up PR; until then, do not run
  `bootstrap` on a vault you intend to use with 0.4.
- **`skills/remove_wiki/SKILL.md`** — targets `topics/<topic>.md`
  and `[[topics/<topic>]]` back-link markers. Will be updated to
  target `wiki/<domain>/<filename>.md` and `[[wiki/<domain>/<filename>]]`
  in the same follow-up.

The three 0.4 skills (`process_clippings`, `research`, `add_wiki`) and
the shared references (`_shared/note-schema.md`,
`_shared/wiki-router.md`) are the only paths that emit the new
layout. The other three are still 0.3.x.

## Acceptance criteria

See `phases/obsidian-topic-organizer/step{0..4}.md` for per-step AC.
