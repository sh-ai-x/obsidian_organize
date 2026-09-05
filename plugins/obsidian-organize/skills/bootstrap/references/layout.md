# bootstrap — canonical layout

The `obsidian-organize:bootstrap` skill creates this layout. All paths are
relative to the vault root.

```
<vault>/
├── Clippings/
│   ├── .keep                 # marker so empty dir is preserved
│   └── processed/            # raw clippings archived after triage
│       └── .keep
├── wiki/
│   ├── .keep
│   └── <topic>/              # one subdir per topic
│       ├── .keep
│       └── README.md         # the canonical topic note
├── wiki-map.md               # markdown index; one row per topic
├── _research/
│   └── .keep
├── _archive/
│   └── research/
│       └── .keep
├── topics/
│   └── .keep                 # alternative location for plugin-generated topic notes
├── .obsidian/                # Obsidian app config (left alone if present)
└── README.md                 # top-level vault README (left alone if present)
```

## Per-path contracts

| Path | Owner | Notes |
|---|---|---|
| `Clippings/` | upstream `process-clippings` | Raw clippings land here. Untouched by `bootstrap` after creation. |
| `Clippings/processed/` | upstream `process-clippings` | Triage output. Untouched by `bootstrap`. |
| `wiki/` | `obsidian-organize:add_wiki` | Topic-organized notes. `bootstrap` creates the dir + `.keep`; never writes inside `<topic>/` unless `--topics` is passed. |
| `wiki/<topic>/README.md` | `obsidian-organize:add_wiki` | Canonical topic note. `bootstrap --topics` seeds a minimal frontmatter (`topic` + `seeded-by`); the real promotion replaces it. |
| `wiki-map.md` | `obsidian-organize:add_wiki` (append) + `obsidian-organize:remove_wiki` (remove row) | Markdown index. `bootstrap` writes the template; the `add_wiki` skill appends between the auto-start / auto-end markers; `remove_wiki` removes the matching row. |
| `_research/` | `obsidian-organize:research` (write) + `obsidian-organize:remove_wiki` (move) | Staged inputs for promotion. |
| `_archive/research/` | `obsidian-organize:remove_wiki` | Archive target for retired staged files. |
| `topics/` | optional alternative layout | Not used by the plugin's default flow; reserved for users who prefer flat topic notes over `wiki/<topic>/`. |
| `.obsidian/` | Obsidian app | Created by Obsidian on first open. `bootstrap` never writes inside. |
| `README.md` | vault owner | Top-level README. `bootstrap` never overwrites. |

## wiki-map.md template

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

The `add_wiki` skill inserts rows between the two markers, one per topic:

```
- [[wiki/hermes-protocol/README|hermes-protocol]] — created 2026-09-05
```

`remove_wiki` removes the matching row.

## Worked example (after `bootstrap --topics "hermes-protocol,wire-protocols"`)

```
<vault>/
├── Clippings/
│   ├── .keep
│   └── processed/.keep
├── wiki/
│   ├── .keep
│   ├── hermes-protocol/
│   │   ├── .keep
│   │   └── README.md         # status: stub, will be replaced on add_wiki
│   └── wire-protocols/
│       ├── .keep
│       └── README.md
├── wiki-map.md               # template + auto-marker block
├── _research/.keep
├── _archive/research/.keep
└── topics/.keep
```
