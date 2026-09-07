---
name: obsidian-organize:add_wiki
description: Write a new Karpathy-style LLM-Wiki leaf note — into the right wiki/<domain>/ locally in --mode=single, or into the matching mybotagent/hermes-wiki-super sub-repo in --mode=super. Takes free-text input or a staged _research/ file. Use when a topic note is wanted and you want it to land in the right place with proper Obsidian graph links.
---

# obsidian-organize:add_wiki

The "give me a topic and get a leaf note" skill. It accepts the input in
two ways and writes the same kind of output in both cases: a proper
Karpathy-style leaf note under `wiki/<domain>/`, with flat tags, an
explicit `related:` list, a TL;DR blockquote, and a `## Related` section
whose `[[wikilinks]]` make the Obsidian graph view work.

## Invocation

```
/obsidian-organize:add_wiki <topic-or-content> [--mode=super|single] [--force] [--dry-run] [--no-backlinks]
```

- `<topic-or-content>` is either a topic phrase ("JWT security pitfalls")
  or raw content to be distilled into a leaf note. It can also be a
  topic slug that maps to a staged file.
- The skill may also be invoked **with no argument**; in that case it
  looks for a staged file at `<vault>/_research/<topic>.md` and promotes
  it. If the input is a topic that has not been staged, treat the topic
  as the distillation seed and write the leaf note directly.
- `--mode=super|single` — pick the target explicitly; autodetected when
  omitted.
- `--force` — overwrite an existing leaf note (default: refuse).
- `--dry-run` — print the planned write targets and change nothing.
- `--no-backlinks` — skip the step that adds the new note to sibling
  notes' `## Related` sections.

## Two modes

- **`--mode=super`** — each knowledge domain is its own GitHub repo under
  `mybotagent/`, mounted as a submodule under `wiki/`. **Read
  `../_shared/hermes-super.md` first** and follow it for sub-repo
  resolution, the LLM-Wiki page format, the two-level commit, and
  new-repo creation. The output uses the sub-repo's content-page format,
  not the local leaf-note shape.
- **`--mode=single`** — the leaf lands in this one repo under
  `wiki/<domain>/`, per the Behavior section below.

When no `--mode` is given, autodetect at the **resolved vault root**
(`$OBSIDIAN_VAULT`, or the vault path passed as the first argument) —
not the current working directory, which may differ. State the detected
mode in the output so the choice is never silent. Detection has three
outcomes, not two; `ambiguous` must not collapse into `single`, or the
skill would silently pick a mode in exactly the cases that warrant asking:

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
entirely. `--mode=single` inside a super-repo clone is legitimate — it
keeps a topic local instead of publishing it to its own repo.

`--local` is accepted as a deprecated alias for `--mode=single`.

## Reference

- `../_shared/note-schema.md` — canonical leaf-note shape and frontmatter
  (`--mode=single`)
- `../_shared/wiki-router.md` — which `wiki/<domain>/` a topic belongs in
- `../_shared/hermes-super.md` — `--mode=super` invariants (SSOT)

## Behavior — `--mode=super`

> **Publish guard:** follow the **Confirm before publishing** section in
> `../_shared/hermes-super.md` before the first non-`--dry-run` push of a
> session. `--dry-run` cannot be the brake.

1. Resolve the input the same way (Behavior — `--mode=single` § Input
   resolution). Fail if the topic/file is missing and no argument was
   given.
2. Distill the input to the same shape (Behavior — `--mode=single` §
   Steps 2). The output is a content page, not a leaf note — write it in
   the sub-repo's format per `../_shared/hermes-super.md` § Step 2.
3. Resolve which existing sub-repo owns the domain, reading `.gitmodules`,
   `wiki-map.md`, and the sub-repos' `*-hub.md` files. Prefer an
   existing domain — a facet of a covered domain becomes a page inside
   it, not a new repo. Only create a repo when nothing covers it, and
   say which and why first.
4. Add a `[[wikilink]]` row to that sub-repo's hub under the fitting
   section, and bump the hub's `Last updated:`. Skip if a row for the
   page already exists, so re-runs do not duplicate rows.
5. Commit and push **inside the submodule**, then bump the pointer in
   the super repo — or, only if the tree was clean beforehand, the
   super repo's `sync.sh` (which commits and pushes *every* dirty
   submodule, not just this run's; see the caveat in
   `_shared/hermes-super.md`).
6. Only after the push succeeds, update the staged file's frontmatter
   (if one was used): `status: promoted`, `promoted_to:
   <owner>/<repo>#<path>`, `updated: <ISO-8601>`. Marking it promoted
   before the push would strand the research with nothing published.

## Behavior — `--mode=single`

### Input resolution

1. **If `$ARGUMENTS` is non-empty** → use it as the topic/seed.
2. **Else, if a staged file exists at `<vault>/_research/<topic>.md`**
   for the topic the user mentions → read it and treat its body as
   source material to distill.
3. **Else** → ask the user once for a one-line topic. If they give
   one, proceed. If they give a longer description, treat that as the
   seed.

If both 1 and 2 apply, prefer 1 (the user's current instruction is
more recent than any staged file).

### Steps

1. **Resolve the topic and read the input.** If `$ARGUMENTS` is empty
   and no staged file exists, ask once for a topic. Stop and wait for
   the answer. Parse the input: subject, key claims, any sources/URLs,
   any pre-existing tags.

2. **Distill.** Apply the distillation rules from `process_clippings` §
   1-2: read once, keep only non-obvious insight, replace prose with
   tables/code where denser, target 1-5 KB.

3. **Pick the destination.** Read `../_shared/wiki-router.md` and pick
   `wiki/<domain>/`. If the destination is unclear, **stop and ask the
   user**.

4. **Pick the filename.** Same rules as `process_clippings` § 4
   (numbered sequence, else kebab-case, else date suffix on collision).
   If `--force` is set, you may overwrite an existing file with the
   same name.

5. **Write the leaf note.** Path: `<vault>/wiki/<domain>/<filename>.md`.
   Build the frontmatter per `_shared/note-schema.md` (flat tags,
   `related:` list with 2-5 entries, `source:` if the note has one, no
   hierarchical tag prefixes). Body: H1, TL;DR blockquote, sections,
   `## Related` with `[[wikilinks]]`.

   If a leaf note already exists at that path and `--force` is **not**
   set, refuse and surface the existing path so the user can decide.

6. **Update the domain's `log.md` and the root `wiki-map.md`.** Same
   shape as `process_clippings` § 6 and § 7.

7. **Update sibling notes' `## Related`.** Same rule as
   `process_clippings` § 8: only when the relationship is obvious from
   the content. Skip if `--no-backlinks` is set.

8. **Mark the staged file as promoted (if one was used).** If the
   input came from `<vault>/_research/<topic>.md`:
   - Update its frontmatter: `status: promoted`, `promoted_to:
     wiki/<domain>/<filename>.md`, `updated: <ISO-8601>`.
   - Leave the body in place — it is now the source of record and may
     still be useful for audit.

   If the input did not come from a staged file, skip this step.

## Edge cases

- Topic not provided and no staged file → ask once, stop.
- Destination wiki unclear → ask once, stop. Do not guess.
- Leaf note already exists at the target path → refuse unless
  `--force` is set. Surface the path so the user can rename or update
  the existing one.
- Source URL / author / date missing → omit those fields from
  frontmatter. Do not invent them.
- Tags empty in the input → pick 3-7 keywords from the body. If the
  body is too thin to tag, ask the user for 3-5 keywords.
- In `--mode=super`, if `gh` is unauthenticated or cannot reach
  `mybotagent`, stop and say so. Do not silently fall back to writing
  locally — that looks like success while nothing synced.

## Anti-patterns

See `../_shared/note-schema.md` § Anti-patterns — what not to write.

## See also

- `../_shared/note-schema.md` — canonical leaf-note shape and frontmatter
- `../_shared/wiki-router.md` — when to ask vs. when to route
- `../_shared/hermes-super.md` — `--mode=super` SSOT
- `obsidian-organize:process_clippings` — same shape, but the input is a
  raw clipping instead of a topic
- `obsidian-organize:research` — stages source material for later
  promotion; if the user is bringing multiple sources together for one
  note, prefer `research` → `add_wiki`
- `obsidian-organize:remove_wiki` — retire a leaf note and clean up
  the back-links
- `obsidian-organize:bootstrap` — creates the vault layout this skill
  writes into
- `hermes-wiki-super` — the vault convention being mirrored
