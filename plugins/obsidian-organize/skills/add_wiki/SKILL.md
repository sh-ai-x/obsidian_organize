---
name: obsidian-organize:add_wiki
description: Write a new Karpathy-style LLM-Wiki leaf note into the right wiki/<domain>/, taking either free text/argument input directly or staging the input through _research/ first. Use when a topic note is wanted and you want it to land in the right place with proper Obsidian graph links.
---

# obsidian-organize:add_wiki

The "give me a topic and get a leaf note" skill. It accepts the input in
two ways and writes the same kind of output in both cases: a proper
Karpathy-style leaf note under `wiki/<domain>/`, with flat tags, an
explicit `related:` list, a TL;DR blockquote, and a `## Related`
section whose `[[wikilinks]]` make the Obsidian graph view work.

## Invocation

```
/obsidian-organize:add_wiki <topic-or-content>
```

- `<topic-or-content>` is either a topic phrase ("JWT security
  pitfalls") or raw content to be distilled into a leaf note.
- The skill may also be invoked **with no argument**; in that case it
  looks for a staged file at `<vault>/_research/<topic>.md` and
  promotes it. If the input is a topic that has not been staged, treat
  the topic as the distillation seed and write the leaf note directly.
- `--force` — overwrite an existing leaf note (default: refuse).
- `--dry-run` — print the planned write targets and change nothing.
- `--no-backlinks` — skip the step that adds the new note to sibling
  notes' `## Related` sections.

## Reference

- `../_shared/note-schema.md` — canonical leaf-note shape (read first)
- `../_shared/wiki-router.md` — which `wiki/<domain>/` a topic belongs in
- `obsidian-organize:process_clippings` — same shape, but the input is
  a raw clipping instead of a topic/argument

## Input resolution

1. **If `$ARGUMENTS` is non-empty** → use it as the topic/seed.
2. **Else, if a staged file exists at `<vault>/_research/<topic>.md`**
   for the topic the user mentions → read it and treat its body as
   source material to distill.
3. **Else** → ask the user once for a one-line topic. If they give one,
   proceed. If they give a longer description, treat that as the seed.

If both 1 and 2 apply, prefer 1 (the user's current instruction is more
recent than any staged file).

## Steps

### 1. Resolve the topic and read the input

- If `$ARGUMENTS` is empty and no staged file exists, ask once for a
  topic. Stop and wait for the answer.
- Parse the input. Extract: subject, key claims, any sources/URLs,
  any pre-existing tags.

### 2. Distill

Apply the distillation rules from `process_clippings` § 1–2: read
once, keep only non-obvious insight, replace prose with tables/code
where denser, target 1–5 KB.

### 3. Pick the destination

Read `../_shared/wiki-router.md` and pick `wiki/<domain>/`. If the
destination is unclear, **stop and ask the user**.

### 4. Pick the filename

Same rules as `process_clippings` § 4 (numbered sequence, else
kebab-case, else date suffix on collision). If `--force` is set, you
may overwrite an existing file with the same name.

### 5. Write the leaf note

Path: `<vault>/wiki/<domain>/<filename>.md`.

Build the frontmatter per `_shared/note-schema.md` (flat tags,
`related:` list with 2–5 entries, `source:` if the note has one, no
hierarchical tag prefixes).

Body: H1, TL;DR blockquote, sections, `## Related` with
`[[wikilinks]]`.

If a leaf note already exists at that path and `--force` is **not**
set, refuse and surface the existing path so the user can decide.

### 6. Update the domain's `log.md` and the root `wiki-map.md`

Same shape as `process_clippings` § 6 and § 7.

### 7. Update sibling notes' `## Related`

Same rule as `process_clippings` § 8: only when the relationship is
obvious from the content. Skip if `--no-backlinks` is set.

### 8. Mark the staged file as promoted (if one was used)

If the input came from `<vault>/_research/<topic>.md`:

- Update its frontmatter: `status: promoted`, `promoted_to:
  wiki/<domain>/<filename>.md`, `updated: <YYYY-MM-DD>`.
- Leave the body in place — it is now the source of record and may
  still be useful for audit.

If the input did not come from a staged file, skip this step.

## Edge cases

- Topic not provided and no staged file → ask once, stop.
- Destination wiki unclear → ask once, stop. Do not guess.
- Leaf note already exists at the target path → refuse unless
  `--force` is set. Surface the path so the user can rename or
  update the existing one.
- Source URL / author / date missing → omit those fields from
  frontmatter. Do not invent them.
- Tags empty in the input → pick 3–7 keywords from the body. If the
  body is too thin to tag, ask the user for 3–5 keywords.

## Anti-patterns — see also

- `../_shared/note-schema.md` § Anti-patterns — what not to write
- `../_shared/wiki-router.md` — when to ask vs. when to route

## See also

- `obsidian-organize:process_clippings` — same shape, input is a
  raw clipping instead of a topic.
- `obsidian-organize:research` — stages source material for later
  promotion. If the user is bringing multiple sources together for one
  note, prefer research → add_wiki.
- `obsidian-organize:remove_wiki` — retire a leaf note and clean up
  the back-links.
- `obsidian-organize:bootstrap` — creates the vault layout this skill
  writes into.
- `hermes-wiki-super` — the vault convention being mirrored.
