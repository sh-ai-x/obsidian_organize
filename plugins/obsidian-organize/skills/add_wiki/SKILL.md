---
name: obsidian-organize:add_wiki
description: Promote a staged research file into a topic note in the Obsidian vault. Use when a topic's research is complete and you want a durable, navigable entry point.
---

# obsidian-organize:add_wiki

## What it does

Reads a staged research file at `<vault>/_research/<topic>.md` and writes a
topic note at `<vault>/topics/<topic>.md`. The topic note carries the topic's
sources as `[[wikilink]]` back-references and updates the staged file's
`status` to `promoted`.

## Invocation

```
/obsidian-organize:add_wiki <topic-or-file>
```

- `<topic-or-file>` is either a topic slug (e.g. `hermes-protocol`) or the
  direct path to a staged research file.
- `--force` — overwrite an existing topic note (default: refuse).
- `--no-backlinks` — skip the reverse-wikilink pass (useful for dry runs).

## Behavior

1. Resolve the staged file: `<vault>/_research/<topic>.md`. Fail if missing.
2. Resolve the target: `<vault>/topics/<topic>.md`. Fail if it exists and
   `--force` is not set.
3. Build the topic-note frontmatter per `references/frontmatter.md`:
   ```yaml
   ---
   topic: <topic>
   created: <ISO-8601>
   updated: <ISO-8601>
   tags: [topic/<topic>]
   sources:
     - <url-or-path>
   status: active
   ---
   ```
4. Body sections: `## Summary` (auto-generated from staged `## Notes`),
   `## Sources` (each source as a markdown bullet), `## Related` (any
   detected `[[wikilink]]` candidates from the staged body).
5. Write the topic note.
6. For each source in the staged file's `sources[]`, append a line to the
   source file (if it exists in the vault) that back-links to the new topic
   note:
   ```
   <!-- back-linked from [[topics/<topic>]] on <ISO-8601> -->
   ```
7. Update the staged file's frontmatter: `status: promoted`,
   `promoted_to: topics/<topic>.md`, `updated: <ISO-8601>`.

## Additive design

This skill does **not** replace `hermes-wiki-super/add-wiki`. The existing
skill is the manual workflow; this plugin formalizes it. If the existing
skill is on `PATH` and accepts the same inputs, `add_wiki` may delegate to
it; otherwise it runs the equivalent logic directly. No skill is shadowed.

## Edge cases

- Staged file missing → fail with: "No staged research at <path>. Run
  /obsidian-organize:research <topic> first."
- Topic note already exists → refuse unless `--force`.
- Source file in `sources[]` not present in vault → skip the back-link for
  that source with a warning; do not fail the whole promotion.
- Vault root unset → fail with: "Set OBSIDIAN_VAULT or pass --vault <path>".

## See also

- `references/frontmatter.md` — canonical topic-note frontmatter.
- `obsidian-organize:research` — produces the staged input.
- `obsidian-organize:remove_wiki` — retires a topic note.
