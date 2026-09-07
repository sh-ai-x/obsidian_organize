---
name: obsidian-organize:process_clippings
description: Turn raw files in an Obsidian vault's Clippings/ folder into LLM-Wiki topic entries, either locally under wiki/<topic>/ or into the matching mybotagent/hermes-wiki-super sub-repo, then archive the originals to Clippings/processed/. Use after a batch of clippings lands in the vault.
---

# obsidian-organize:process_clippings

Move each file in `Clippings/` into a topic folder, then archive the original.

## Two targets

Decide the target before writing anything:

- **hermes-wiki-super** — the vault is (or contains) a clone of
  `mybotagent/hermes-wiki-super`, i.e. a `.gitmodules` with `wiki/…` submodule
  entries is present. Each topic lives in its own GitHub repo. **Read
  `../_shared/hermes-super.md` first** and follow it for target resolution,
  file format, the two-level commit, and new-repo creation.
- **plain vault** — no such `.gitmodules`. Everything stays local, per the
  steps below.

Detect it, do not ask:

```bash
grep -q 'submodule "wiki/' .gitmodules 2>/dev/null && echo super || echo plain
```

`--local` forces plain-vault behavior even inside a super-repo clone.

## Invocation

```
/obsidian-organize:process_clippings [<vault-path>] [--dry-run] [--local]
```

Vault root comes from the argument, else `$OBSIDIAN_VAULT`. If neither is set,
stop and say: `Set OBSIDIAN_VAULT or pass the vault path`.

With `--dry-run`, print the plan and change nothing — including no `gh` writes,
no commits, and no repo creation.

## Steps — plain vault

For each `*.md` directly inside `<vault>/Clippings/` — skip
`Clippings/processed/`, dotfiles, and `*.keep`:

1. **Pick the topic.** Use the file's first `# H1`. If there is no H1, use the
   filename without its extension. Lowercase it, and replace spaces and
   underscores with hyphens. Keep non-ASCII characters as they are, so Korean
   and other CJK headings stay readable as folder names. Never let a topic
   contain `/`, `\`, or be made only of dots — if it would, use `untitled`.

2. **Write the topic hub** at `wiki/<topic>/README.md`, only if it does not
   already exist:

   ```markdown
   # <topic>

   > <one-line description of the topic> — Karpathy-style LLM Wiki
   > Created: <YYYY-MM-DD>

   ## Contents

   - [clippings/](clippings/) — raw research sources indexed here.
   ```

   You write the description line — one sentence, from reading the clipping.

3. **Write the clipping page** at `wiki/<topic>/clippings/<filename>`, with the
   original body kept verbatim under this frontmatter:

   ```markdown
   ---
   type: clipping
   topic: <topic>
   source: <original filename>
   processed: <YYYY-MM-DD>
   ---

   <original body, unchanged>
   ```

4. **Add a row to `wiki-map.md`** at the vault root, pointing at the new topic.
   Create the file with a `# Wiki Map` heading first if it is missing. Skip if a
   row for the same topic and filename is already there, so re-runs do not
   duplicate rows.

   ```markdown
   | [[wiki/<topic>/README|<topic>]] | `<filename>` | <YYYY-MM-DD> |
   ```

5. **Archive the original** by moving it to `Clippings/processed/<filename>`.
   Do this last: if anything above failed, the file stays in `Clippings/` and a
   re-run picks it up again. Moving it first would silently lose the clipping.
   If that name is taken, append a timestamp — `a.md` →
   `a-20260905T120000Z.md`.

## Steps — hermes-wiki-super

Same topic derivation (step 1 above), then per `../_shared/hermes-super.md`:

1. Resolve which existing sub-repo owns the topic, reading `.gitmodules`,
   `wiki-map.md`, and the sub-repos' `*-hub.md` files. Prefer an existing
   domain; a facet of a covered domain becomes a page inside it, not a new repo.
2. Write the clipping as a content page inside that sub-repo, in the LLM-Wiki
   content-page format (frontmatter with `tags` / `related` / `source`).
3. Add a `[[wikilink]]` row to that sub-repo's hub under the fitting section and
   bump the hub's `Last updated:`.
4. Commit and push **inside the submodule**, then bump the pointer in the super
   repo — or run the super repo's `sync.sh`, which does both for every changed
   submodule.
5. Only if no sub-repo covers the domain, create one and register it in
   `.gitmodules` + `wiki-map.md`. Say which repo you are creating and why
   before doing it.
6. Archive the original to `Clippings/processed/` **last**, only after the push
   succeeded — otherwise the clipping is gone and the content never landed.

Then print a short summary: how many were processed, each `topic ← filename`
with the sub-repo it landed in, and anything skipped and why.

## Notes

- `Clippings/` missing or empty → say `nothing to process` and stop.
- Two clippings on one topic → both go under the same topic; the hub is written
  once and gets two rows.
- Strip a leading UTF-8 BOM before looking for the H1, and do not carry it into
  the file you write.
- If a file cannot be read as UTF-8, skip it and name it in the summary rather
  than failing the whole batch.
- In super-repo mode, if `gh` is unauthenticated or cannot reach `mybotagent`,
  stop and say so. Do not silently fall back to writing locally — that looks
  like success while nothing synced.

## See also

- `../_shared/hermes-super.md` — sub-repo resolution, LLM-Wiki format, two-level
  commit, new-repo creation.
- `obsidian-organize:bootstrap` — creates the plain-vault layout.
- `obsidian-organize:add_wiki` — promotes staged research into a topic note, and
  in super-repo mode targets the same sub-repos.
- `hermes-wiki-super` — the vault convention being mirrored.
