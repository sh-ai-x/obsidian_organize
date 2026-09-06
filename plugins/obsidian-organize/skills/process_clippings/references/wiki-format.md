# wiki-format — output shapes for `obsidian-organize:process_clippings`

This is the LLM-Wiki format this skill writes, modeled on the canonical
`hermes-wiki-super` vault layout.

## Topic- README

Path: `wiki/<topic>/README.md`

```markdown
# <topic>

> <description> — Karpathy-style LLM Wiki
> Created: <YYYY-MM-DDTHH:MM:SSZ>

## Contents

- [clippings/](clippings/) — raw research sources indexed here.

---

<!-- obsidian-organize:topic:auto-start -->
<!-- Each row below is appended by obsidian-organize:process_clippings when a new source lands. -->
<!-- Do not edit by hand; re-running `bootstrap --force` re-seeds. -->
<!-- obsidian-organize:topic:auto-end -->
```

`topic` is the slug derived from the first `# H1` of the first
clipping in the batch (or the filename stem if no H1).

## Per-clipping page

Path: `wiki/<topic>/clippings/<safe-source-filename>.md`

Frontmatter:

```yaml
---
type: clipping
topic: <topic>
source: <original-filename-in-Clippings>
processed: <YYYY-MM-DDTHH:MM:SSZ>
---
```

Body: the original clipping file content verbatim, with leading
newlines stripped so the first non-whitespace line follows the
closing `---` fence directly.

## wiki-map.md row

Appended between the `<!-- obsidian-organize:wiki-map:auto-start -->`
and `<!-- obsidian-organize:wiki-map:auto-end -->` markers, or seeded
at the bottom of the file if the markers is absent:

```markdown
- [[wiki/<topic>/README|<topic>]] — processed `<source-filename>`
```

## Clippings/processed/

The source file is renamed (not copied) into
`Clippings/processed/<safe-source-filename>.md`. If that target
already exists, an ISO-8601 suffix is inserted before the extension
(`a.md` → `a-20260905T120000Z.md`).

## Layout at a glance

```
<vault>/
├── Clippings/
│   ├── foo.md                  # dropped by upstream (e.g. process-clippings)
│   └── processed/
│       └── foo.md              # archived by this skill after success
├── wiki/
│   └── <topic>/
│       ├── README.md           # LLM-Wiki hub, created once per topic
│       └── clippings/
│           └── foo.md          # per-clipping page w/ frontmatter envelope
└── wiki-map.md                 # one row per processed topic
```