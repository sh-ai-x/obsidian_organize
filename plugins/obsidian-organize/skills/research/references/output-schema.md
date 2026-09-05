# research — output schema

The staged research file is the **single source of truth** for `add_wiki`'s
input. This document pins its shape so step 2 can read it deterministically.

## File path

```
<vault>/_research/<topic>.md
```

- `<topic>` is the lowercased, hyphenated topic name.
- Directory `_research/` is created on first use.

## Frontmatter

```yaml
---
topic: <topic>            # string — same as the slug in the file path
created: <ISO-8601>       # string — when this staged file was first written
updated: <ISO-8601>       # string — last append; absent on initial creation
sources:
  - <url-or-path>         # list of strings — each source consumed during research
status: staged            # one of: staged | promoted | archived
promoted_to: <path>       # optional — set by add_wiki once the topic note exists
---
```

`status` lifecycle:

| Value | Set by | Meaning |
|---|---|---|
| `staged` | `research` | New file; not yet promoted. |
| `promoted` | `add_wiki` | A topic note exists; this is now the upstream source. |
| `archived` | `remove_wiki` | Topic was retired; this file moved to `_archive/research/`. |

## Body

```markdown
## Sources

- <source 1> — <one-line caption>
- <source 2> — <one-line caption>

## Notes

> Quoted material goes here. Use `>` for direct quotes and plain text for
> paraphrased notes.
```

## Worked example

```markdown
---
topic: hermes-protocol
created: 2026-09-05T10:00:00Z
sources:
  - https://example.com/hermes-spec
  - ~/Documents/notes/hermes-draft.md
status: staged
---

## Sources

- https://example.com/hermes-spec — Hermes wire-protocol specification, section 4
- ~/Documents/notes/hermes-draft.md — Internal draft from 2026-08-12

## Notes

> "Hermes uses length-prefixed frames with a 4-byte big-endian header."
```
