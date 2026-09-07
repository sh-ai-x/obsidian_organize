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
│   ├── _lib/                     # LEGACY (0.3.x) — see deprecation note in __init__.py
│   ├── bootstrap/
│   │   ├── SKILL.md
│   │   └── references/layout.md
│   ├── process_clippings/
│   │   └── SKILL.md
│   ├── research/
│   │   ├── SKILL.md
│   │   └── references/output-schema.md
│   ├── add_wiki/
│   │   └── SKILL.md
│   └── remove_wiki/
│       ├── SKILL.md
│       └── references/cleanup-rules.md
├── tests/                        # LEGACY (0.3.x) — exercises _lib/ deterministic flow
├── docs/
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
need a one-time migration (see `docs/migration-0.3-to-0.4.md` if
present) before the new layout will render correctly in Obsidian.

## Acceptance criteria

See `phases/obsidian-topic-organizer/step{0..4}.md` for per-step AC.
