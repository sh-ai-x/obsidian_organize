---
name: obsidian-organize:process_clippings
description: Distill raw files in an Obsidian vault's Clippings/ folder into Karpathy-style LLM-Wiki leaf notes. In --mode=single the leaf lands under wiki/<domain>/ in this repo, with domain log + wiki-map updated. In --mode=super it routes into the matching mybotagent/hermes-wiki-super sub-repo instead. In both modes the original is archived to Clippings/processed/. Use after a batch of clippings lands in the vault.
---

# obsidian-organize:process_clippings

Take raw files dropped into `Clippings/`, distill each into a single leaf note
in the right `wiki/<domain>/`, link it into the graph, and archive the original.
Leaf notes follow the convention in `../_shared/note-schema.md` — flat keyword
tags, explicit `related:` list, TL;DR blockquote, and a `## Related` section
with `[[wikilinks]]`. This is what makes Obsidian's graph view work.

## Two modes

- **`--mode=super`** — each domain lives in its own GitHub repo, mounted as a
  submodule under `wiki/` in `mybotagent/hermes-wiki-super`. **Read
  `../_shared/hermes-super.md` first** and follow it for sub-repo resolution,
  the LLM-Wiki hub/content format, the two-level commit, and new-repo
  creation.
- **`--mode=single`** — everything stays in this one repo under
  `wiki/<domain>/`, per the steps below. The leaf-note shape and the
  distillation rules still apply; only the destination and the two-level
  commit are different.

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
entirely. `--mode=single` inside a super-repo clone is legitimate — it keeps
a topic local instead of publishing it to its own repo.

`--local` is accepted as a deprecated alias for `--mode=single`.

## Invocation

```
/obsidian-organize:process_clippings [<vault-path>] [--mode=super|single] [--dry-run]
```

Vault root comes from the argument, else `$OBSIDIAN_VAULT`. If neither is set,
stop and say: `Set OBSIDIAN_VAULT or pass the vault path`.

With `--dry-run`, print the plan and change nothing — including no `gh` writes,
no commits, and no repo creation.

## Reference

- `../_shared/note-schema.md` — canonical leaf-note shape (read first)
- `../_shared/wiki-router.md` — which `wiki/<domain>/` a topic belongs in
- `../_shared/hermes-super.md` — `--mode=super` invariants (SSOT)

## Steps — `--mode=single`

For each `*.md` directly inside `<vault>/Clippings/` — skip
`Clippings/processed/`, dotfiles, and `*.keep`:

### 1. Read the clipping

Read the whole file. Parse its frontmatter. Capture:

- `title:` (or first H1) → becomes the leaf note's H1
- `source:` / `url:` → the leaf note's `source:` frontmatter
- `author:` → include in the body if it identifies the author
- `published:` → include in the body
- `description:` → the seed for the TL;DR blockquote
- `tags:` from the original → candidate tags for the new note (validate against
  `note-schema.md` rules before reusing)

Strip any leading UTF-8 BOM.

### 2. Distill into a leaf note

Read the body once. The clipping is a source; the leaf note is a
**distillation**. Apply these rules:

- Keep only non-obvious, hard-to-rediscover insight. Delete install guides,
  basic tutorials, and anything re-stating official docs.
- Preserve the author's exact phrasing only when it carries unique weight
  (a definition, a quote that crystallizes the concept). Mark the quoted span
  as a blockquote.
- Replace prose with tables / code blocks / ASCII diagrams when those are
  denser.
- Aim for 1–5 KB. If the distilled note exceeds 5 KB, look for sections that
  belong in a separate note and split.

### 3. Pick the destination

Read `../_shared/wiki-router.md` and pick the `wiki/<domain>/` for the
topic. If the destination is unclear, **stop and ask the user** — do not
guess. Guessing creates orphan notes that pollute the graph.

If a new wiki is needed, follow the "New wiki" procedure in the router file.

### 4. Pick the filename

- If the target domain uses numbered pages (`00-…`, `01-…`), continue the
  sequence with the next free number.
- Otherwise use a kebab-case content-derived name (no extension).
- If a file with the same name already exists in the domain, **append** a
  date suffix (`-2026-09-07.md`) rather than overwriting.

### 5. Write the leaf note

Path: `<vault>/wiki/<domain>/<filename>.md`.

Build the frontmatter per `_shared/note-schema.md`. Three things matter most:

- **Tags**: flat keywords, 3–7 entries, all shared with at least one other
  existing note in the domain. Scan the domain's existing notes first;
  reuse their vocabulary.
- **`related:`**: 2–5 vault-relative paths. At least one inside the same
  domain; at least one cross-domain if one exists.
- **`source:`**: the original URL or path from step 1.

Then the body: H1, TL;DR blockquote, sections, `## Related` with
`[[wikilinks]]`.

### 6. Update the domain's `log.md`

Append one entry to `<vault>/wiki/<domain>/log.md`:

```markdown
## [<YYYY-MM-DD>] ingest | <Note Title>
<one-line summary of what was distilled from the clipping>
```

If `log.md` does not exist, create it with a `# <Domain> — Change Log` header
before the first entry.

### 7. Update the root `wiki-map.md`

If the root `wiki-map.md` does not exist, create it with a `# Wiki Map`
header. Append a bullet linking to the new note inside the section for its
domain. Use the form:

```markdown
- [[wiki/<domain>/<filename>|<Note Title>]] — <one-line summary>
```

If a bullet for this exact `domain/filename` already exists, skip the write
(re-runs do not duplicate).

### 8. Update sibling notes' `## Related` (when natural)

If the new note strongly relates to one or two existing notes in the same
domain, add a one-line `## Related` entry to those existing notes pointing
at the new note. This is the only step that edits other people's notes; do it
sparingly and only when the relationship is obvious from the content.

### 9. Archive the original

Move the original from `<vault>/Clippings/<filename>` to
`<vault>/Clippings/processed/<filename>`. Do this **last** — if any prior
step failed, the file stays in `Clippings/` and a re-run picks it up. If
`<vault>/Clippings/processed/<filename>` already exists, append a timestamp:
`<filename>-<YYYYMMDDTHHMMSSZ>.md`.

Then print a short summary: how many were processed, each
`domain/filename ← original filename`, the chosen tags + related links, and
anything skipped and why.

## Steps — `--mode=super`

> **Publish guard:** see the **Confirm before publishing** section in
> `../_shared/hermes-super.md` before any non-`--dry-run` push in
> `--mode=super`. `--dry-run` cannot be the brake: it is opt-in and not all
> writers support it. The flag chooses the target; it does not authorize
> publishing a specific set of files.

Same frontmatter / distillation rules as `--mode=single` steps 1-2, but the
**target** is the resolved sub-repo per `_shared/hermes-super.md`, the
**shape** is the sub-repo content-page format (not a leaf note), and the
**two-level commit** replaces the local write sequence:

1. Read the clipping; pick the topic the same way (first H1, fall back to
   filename). Subject it to the same distillation + sanitization rules.
2. Resolve which existing sub-repo owns the topic, reading `.gitmodules`,
   `wiki-map.md`, and the sub-repos' `*-hub.md` files. Prefer an existing
   domain; a facet of a covered domain becomes a page inside it, not a new
   repo.
3. Write the distilled content as a content page inside that sub-repo
   (frontmatter `tags` / `related` / `source`, body, `## Related` wikilinks),
   using the sub-repo's hub format — not the local `wiki/<domain>/` shape.
4. Add a `[[wikilink]]` row to that sub-repo's hub under the fitting
   section, and bump the hub's `Last updated:`. Skip if a row for the page
   already exists, so re-runs do not duplicate rows.
5. Commit and push **inside the submodule**, then bump the pointer in the
   super repo — or, only if the tree was clean beforehand, the super repo's
   `sync.sh` (which commits and pushes *every* dirty submodule, not just
   this run's; see the caveat in `_shared/hermes-super.md`).
6. Only if no sub-repo covers the domain, create one and register it in
   `.gitmodules` + `wiki-map.md`. Say which repo you are creating and why
   before doing it.
7. Archive the original to `Clippings/processed/` **last**, only after the
   push succeeded — otherwise the clipping is gone and the content never
   landed.

Then print a short summary: how many were processed, each
`topic ← filename` with the sub-repo it landed in, and anything skipped
and why.

## Notes

- `Clippings/` missing or empty → say `nothing to process` and stop.
- Two clippings on the same topic → distill each into its own note; pick
  filenames that distinguish them. Do not merge.
- If a file cannot be read as UTF-8, skip it and name it in the summary
  rather than failing the whole batch.
- Always re-read `wiki-map.md` before writing to it. Preserve the existing
  structure (frontmatter, sections) — append, do not rewrite.
- A "clipping" is the input. A "leaf note" is the output. The two are not
  the same file. Do not copy the clipping into the wiki.
- In `--mode=super`, if `gh` is unauthenticated or cannot reach `mybotagent`,
  stop and say so. Do not silently fall back to writing locally — that
  looks like success while nothing synced.

## Anti-patterns

See `../_shared/note-schema.md` § Anti-patterns — what not to write.

## See also

- `../_shared/note-schema.md` — canonical leaf-note shape and frontmatter
- `../_shared/wiki-router.md` — when to ask vs. when to route
- `../_shared/hermes-super.md` — `--mode=super` SSOT
- `obsidian-organize:add_wiki` — same leaf-note shape, but takes free text or
  a staged `_research/` file instead of a raw clipping
- `obsidian-organize:research` — produces staged research files that
  `add_wiki` can later promote
- `obsidian-organize:bootstrap` — creates the vault layout this skill writes
  into
- `hermes-wiki-super` — the vault convention being mirrored
