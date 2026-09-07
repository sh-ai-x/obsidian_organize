---
name: obsidian-organize:process_clippings
description: Turn raw files in an Obsidian vault's Clippings/ folder into LLM-Wiki topic entries — in one repo under wiki/<topic>/ (--mode=single) or into the matching mybotagent/hermes-wiki-super sub-repo (--mode=super) — then archive the originals to Clippings/processed/. Use after a batch of clippings lands in the vault.
---

# obsidian-organize:process_clippings

Move each file in `Clippings/` into a topic folder, then archive the original.

## Two modes

- **`--mode=super`** — each topic lives in its own GitHub repo, mounted as a
  submodule under `wiki/` in `mybotagent/hermes-wiki-super`. **Read
  `../_shared/hermes-super.md` first** and follow it for sub-repo resolution,
  file format, the two-level commit, and new-repo creation.
- **`--mode=single`** — everything stays in one repo under `wiki/<topic>/`, per
  the single-repo steps below.

When no `--mode` is given, autodetect at the **resolved vault root**
(`$OBSIDIAN_VAULT`, or the vault path passed as the first argument) — not the
current working directory, which may differ. State the detected mode in the
output so the choice is never silent. Detection has three outcomes, not two;
`ambiguous` must not collapse into `single`, or the skill would silently pick
a mode in exactly the cases that warrant asking:

```bash
vault="${OBSIDIAN_VAULT:-<vault-path-from-arg>}"
gm="$vault/.gitmodules"
if [ ! -e "$gm" ]; then
  echo single                        # no submodules at all -> one repo
elif ! grep -q 'submodule "' "$gm" 2>/dev/null; then
  echo ambiguous                     # unreadable or unparseable -> ask
elif grep -q 'submodule "wiki/' "$gm"; then
  echo super                         # wiki/ submodules -> constellation
else
  echo ambiguous                     # submodules, but none under wiki/ -> ask
fi
```

On `ambiguous`, stop and ask: say what was found and which mode you propose.
Never resolve an `ambiguous` result by falling through to a default.

The `cd "$vault"` that precedes every path write in the steps below also
applies the detector; do not `cd` again just for the check.

An explicit `--mode` always wins over autodetection and skips this check
entirely. `--mode=single` inside a super-repo clone is legitimate — it keeps a
topic local instead of publishing it to its own repo.

## Invocation

```
/obsidian-organize:process_clippings [<vault-path>] [--mode=super|single] [--dry-run]
```

Vault root comes from the argument, else `$OBSIDIAN_VAULT`. If neither is set,
stop and say: `Set OBSIDIAN_VAULT or pass the vault path`.

With `--dry-run`, print the plan and change nothing — including no `gh` writes,
no commits, and no repo creation.

`--local` is accepted as a deprecated alias for `--mode=single`.

## Steps — `--mode=single`

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

## Steps — `--mode=super`

> **Publish guard:** see the **Confirm before publishing** section in `../_shared/hermes-super.md` before any non-`--dry-run` push in `--mode=super`.

Same topic derivation (step 1 above), then per `../_shared/hermes-super.md`:

1. Resolve which existing sub-repo owns the topic, reading `.gitmodules`,
   `wiki-map.md`, and the sub-repos' `*-hub.md` files. Prefer an existing
   domain; a facet of a covered domain becomes a page inside it, not a new repo.
2. Write the clipping as a content page inside that sub-repo, in the LLM-Wiki
   content-page format (frontmatter with `tags` / `related` / `source`).
3. Add a `[[wikilink]]` row to that sub-repo's hub under the fitting section and
   bump the hub's `Last updated:`.
4. Commit and push **inside the submodule**, then bump the pointer in the super
   repo — or, only if the tree was clean beforehand, the super repo's `sync.sh`
  (which commits and pushes *every* dirty submodule, not just this run's; see
  the caveat in `_shared/hermes-super.md`).
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
- In `--mode=super`, if `gh` is unauthenticated or cannot reach `mybotagent`,
  stop and say so. Do not silently fall back to writing locally — that looks
  like success while nothing synced.

## See also

- `../_shared/hermes-super.md` — sub-repo resolution, LLM-Wiki format, two-level
  commit, new-repo creation.
- `obsidian-organize:bootstrap` — creates the single-repo layout.
- `obsidian-organize:add_wiki` — promotes staged research into a topic note, and
  in `--mode=super` targets the same sub-repos.
- `hermes-wiki-super` — the vault convention being mirrored.
