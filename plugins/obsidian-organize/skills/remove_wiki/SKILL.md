---
name: obsidian-organize:remove_wiki
description: Retire a topic note, archive its staged research, and clean up back-links. Use when a topic has decayed or is no longer relevant.
---

# obsidian-organize:remove_wiki

## What it does

Identifies a topic by its `topic:` frontmatter key, archives the staged
research file, removes the topic note, and strips the back-link from each
source file in the vault.

## Invocation

```
/obsidian-organize:remove_wiki <topic>
```

- `--dry-run` — print the planned mutations and exit 0 without writing.
- `--keep-staged` — leave the staged research file in place (still flips
  its `status` to `archived`); default is to move it to `_archive/research/`.

## Behavior

1. Resolve the topic note: `<vault>/topics/<topic>.md`. Fail if missing.
2. Resolve the staged file: `<vault>/_research/<topic>.md`. Warn if missing
   and continue.
3. Compute archive path: `<vault>/_archive/research/<topic>-<ISO-8601>.md`,
   where `<ISO-8601>` is the current time with seconds (e.g.
   `2026-09-05T11-00-00Z`). `--` is used instead of `:` for filesystem safety.
4. Scan the vault (default root: `<vault>/`, excluding `topics/`,
   `_research/`, `_archive/`) for the back-link marker
   `<!-- back-linked from [[topics/<topic>]] on <ISO-8601> -->`. Remove the
   line containing it from each source file.
5. Move the staged file to the archive path. Update its frontmatter:
   `status: archived`.
6. Update the topic note's frontmatter (do not delete it yet):
   `status: retired`, `retired_at: <ISO-8601>`,
   `retired_to: <archive-path>`.
7. Delete the topic note.
8. Print a summary: how many source files were touched, where the staged
   file moved.

## Edge cases

- Topic note missing → fail with: "No active topic at <path>. Nothing to
  remove."
- Staged file missing → warn, continue (the topic can still be retired
  without its staged input).
- Archive directory missing → create it.
- Source file already has the back-link removed → no-op for that file.
- Vault root unset → fail with: "Set OBSIDIAN_VAULT or pass --vault <path>".

## See also

- `references/cleanup-rules.md` — scan-root, archive naming, back-link
  removal algorithm.
- `obsidian-organize:add_wiki` — produces the topic note.
- `obsidian-organize:research` — produces the staged input.
