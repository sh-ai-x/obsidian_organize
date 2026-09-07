---
name: obsidian-organize:process_clippings
description: Turn raw files in an Obsidian vault's Clippings/ folder into LLM-Wiki topic entries under wiki/<topic>/, then archive the originals to Clippings/processed/. Use after a batch of clippings lands in the vault.
---

# obsidian-organize:process_clippings

Move each file in `Clippings/` into a topic folder under `wiki/`, then
archive the original.

## Invocation

```
/obsidian-organize:process_clippings [<vault-path>] [--dry-run]
```

Vault root comes from the argument, else `$OBSIDIAN_VAULT`. If neither is
set, stop and say: `Set OBSIDIAN_VAULT or pass the vault path`.

With `--dry-run`, print the plan and change nothing.

## Steps

For each `*.md` directly inside `<vault>/Clippings/` — skip
`Clippings/processed/`, dotfiles, and `*.keep`:

1. **Pick the topic.** Use the file's first `# H1`. If there is no H1,
   use the filename without its extension. Lowercase it, and replace
   spaces and underscores with hyphens. Keep non-ASCII characters as they
   are, so Korean and other CJK headings stay readable as folder names.
   Never let a topic contain `/`, `\`, or be made only of dots — if it
   would, use `untitled` instead.

2. **Write the topic hub** at `wiki/<topic>/README.md`, only if it does
   not already exist:

   ```markdown
   # <topic>

   > <one-line description of the topic> — Karpathy-style LLM Wiki
   > Created: <YYYY-MM-DD>

   ## Contents

   - [clippings/](clippings/) — raw research sources indexed here.
   ```

   You write the description line — one sentence, from reading the
   clipping.

3. **Write the clipping page** at `wiki/<topic>/clippings/<filename>`,
   with the original body kept verbatim under this frontmatter:

   ```markdown
   ---
   type: clipping
   topic: <topic>
   source: <original filename>
   processed: <YYYY-MM-DD>
   ---

   <original body, unchanged>
   ```

4. **Add a row to `wiki-map.md`** at the vault root, pointing at the new
   topic. Create the file with a `# Wiki Map` heading first if it is
   missing. Skip this if a row for the same topic and filename is already
   there, so re-runs do not duplicate rows.

   ```markdown
   | [[wiki/<topic>/README|<topic>]] | `<filename>` | <YYYY-MM-DD> |
   ```

5. **Archive the original** by moving it to
   `Clippings/processed/<filename>`. Do this last: if anything above
   failed, the file stays in `Clippings/` and a re-run picks it up again.
   Moving it first would silently lose the clipping. If that name is
   taken, append a timestamp — `a.md` → `a-20260905T120000Z.md`.

Then print a short summary: how many were processed, each
`topic ← filename`, and anything skipped and why.

## Notes

- `Clippings/` missing or empty → say `nothing to process` and stop.
- Two clippings on one topic → both go under the same
  `wiki/<topic>/clippings/`; the topic README is written once.
- Strip a leading UTF-8 BOM before looking for the H1, and do not carry
  it into the file you write.
- If a file cannot be read as UTF-8, skip it and name it in the summary
  rather than failing the whole batch.

## See also

- `obsidian-organize:bootstrap` — creates the vault layout this skill
  writes into.
- `obsidian-organize:add_wiki` — promotes staged research into
  `topics/<topic>.md`. It does not touch `wiki/` or `wiki-map.md`;
  this skill is the only writer of `wiki-map.md`.
- `hermes-wiki-super` — the vault convention being mirrored.
