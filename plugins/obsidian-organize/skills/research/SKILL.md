---
name: obsidian-organize:research
description: Gather source material on a topic and produce a staged research file in the Obsidian vault. Use when starting a new topic or when extending an existing one.
---

# obsidian-organize:research

## What it does

Takes a topic (string) and optional source inputs (URLs, file paths, pasted
quotes) and writes a single staged research file at:

```
<vault>/_research/<topic>.md
```

The file's frontmatter, body shape, and tag conventions are inherited from
`hermes-wiki-super/process-clippings` — see `references/output-schema.md`.

## Invocation

```
/obsidian-organize:research <topic>
```

Optional flags (parsed from prompt context, not a CLI):
- `--source URL` — append a source URL to the staged file's `sources[]`.
- `--from <path>` — read an existing file as input material.
- `--append` — if the staged file already exists, append new sources; otherwise create.

## Behavior

1. Compute the target path: `<vault>/_research/<topic>.md`. Topic is
   lowercased and spaces become hyphens.
2. If the file exists and `--append` is not set, refuse to overwrite.
3. Build the frontmatter per `references/output-schema.md`:
   ```yaml
   ---
   topic: <topic>
   created: <ISO-8601>
   sources:
     - <url or path>
   status: staged
   ---
   ```
4. Write the body. The body contains a `## Sources` section listing each
   source as a markdown bullet with a one-line caption, and a
   `## Notes` section with any pasted quotes.
5. Print the resolved path so the operator can review before invoking
   `obsidian-organize:add_wiki`.

## Edge cases

- Topic contains characters outside `[a-z0-9-]` → fail with a clear error.
- `_research/` does not exist → create it.
- Vault root is unset → fail with: "Set OBSIDIAN_VAULT or pass --vault <path>".

## See also

- `references/output-schema.md` — canonical frontmatter + body shape.
- `hermes-wiki-super/process-clippings` — the upstream skill whose output
  shape this skill mirrors.
