---
name: obsidian-organize:research
description: Gather source material on a topic and produce a staged research file in the Obsidian vault using the hermes-wiki-super LLM-Wiki frontmatter shape, so add_wiki can promote it into a proper leaf note later. Use when starting a new topic or when extending an existing one.
---

# obsidian-organize:research

Take a topic and optional source inputs (URLs, file paths, pasted
quotes) and write a staged research file at:

```
<vault>/_research/<topic>.md
```

The file's frontmatter and tag conventions follow the
`hermes-wiki-super/ai-agent-wiki` LLM-Wiki shape — see
`../_shared/note-schema.md`. That way `add_wiki` can promote the staged
file into a leaf note without re-tagging it from scratch.

## Invocation

```
/obsidian-organize:research <topic>
```

Optional flags (parsed from prompt context, not a CLI):
- `--source URL` — append a source URL to the staged file's
  `sources[]`.
- `--from <path>` — read an existing file as input material.
- `--append` — if the staged file already exists, append new sources;
  otherwise create.

## Reference

- `../_shared/note-schema.md` — the leaf-note shape this staged file
  will be promoted into.
- `../_shared/wiki-router.md` — which `wiki/<domain>/` the eventual
  leaf note will land in (helpful to pre-stage `related:` entries).

## Behavior

1. Compute the target path: `<vault>/_research/<topic>.md`. Topic is
   lowercased and spaces become hyphens. Use only `[a-z0-9-]`.
2. If the file exists and `--append` is not set, refuse to overwrite.
3. Build the frontmatter per `_shared/note-schema.md` (the LLM-Wiki
   shape), with the staged lifecycle field `status: staged` added:
   ```yaml
   ---
   topic: <topic>
   tags: ["<keyword-1>", "<keyword-2>", ...]
   related: ["<other-note>", ...]
   created: <YYYY-MM-DD>
   updated: <YYYY-MM-DD>
   sources:
     - <url or path>
   status: staged
   promoted_to: <path>     # optional — set by add_wiki once promoted
   ---
   ```
   - `tags:` is a flat keyword list (3–7 entries) — the same shape a
     leaf note uses. Pre-pick tags by reading the existing notes in the
     eventual target domain and reusing their vocabulary.
   - `related:` lists vault-relative paths to other notes that the
     eventual leaf note should link to.
   - `sources:` is the list of source URLs / paths gathered during
     research.
4. Write the body. The body contains a `## Sources` section listing
   each source as a markdown bullet with a one-line caption, and a
   `## Notes` section with any pasted quotes or paraphrases.
5. Print the resolved path so the operator can review before invoking
   `obsidian-organize:add_wiki`.

## Edge cases

- Topic contains characters outside `[a-z0-9-]` → fail with a clear
  error.
- `_research/` does not exist → create it.
- Vault root is unset → fail with: "Set OBSIDIAN_VAULT or pass
  --vault <path>".

## See also

- `../_shared/note-schema.md` — the leaf-note shape this staged file
  will become.
- `obsidian-organize:add_wiki` — promotes a staged file (or free
  text) into a leaf note.
- `obsidian-organize:process_clippings` — same leaf-note shape, but
  the input is a raw clipping instead of staged research.
