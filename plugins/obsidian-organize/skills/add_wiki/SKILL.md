---
name: obsidian-organize:add_wiki
description: Write a new Karpathy-style LLM-Wiki leaf note — into the right wiki/<domain>/ locally in --mode=single, or into the matching mybotagent/hermes-wiki-super sub-repo in --mode=super. Supports flat and hierarchical layouts (per-section leaf notes under wiki/<domain>/<slug>/<section>.md, or wiki/<domain>/<major>/<slug>/<section>.md with --major). Takes free-text input or a staged _research/ file. Use when a topic note is wanted and you want it to land in the right place with proper Obsidian graph links.
---

# obsidian-organize:add_wiki

The "give me a topic and get a leaf note" skill. It accepts the input in
two ways and writes the same kind of output in both cases: a proper
Karpathy-style leaf note under `wiki/<domain>/`, with flat tags, an
explicit `related:` list, a TL;DR blockquote, and a `## Related` section
whose `[[wikilinks]]` make the Obsidian graph view work.

## Invocation

```
/obsidian-organize:add_wiki <topic-or-content> [--mode=super|single] [--force] [--dry-run] [--no-backlinks] [--hierarchical] [--major <name>]
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
- `--hierarchical` — promote a multi-section staged research into a
  per-section leaf-note tree under `wiki/<domain>/<slug>/<section>.md`
  with an auto-generated `_index.md` sub-hub. See
  [Hierarchical mode](#hierarchical-mode-multilevel-research) below.
  Auto-enabled when a staged research file has **≥ 5 numbered sections**
  (H2 `## §N …` or H3 `### N. …`), unless `--no-hierarchical` is also
  passed.
- `--major <name>` — only meaningful with `--hierarchical`. Adds one
  extra directory level between `<domain>` and the per-topic directory:
  `wiki/<domain>/<major>/<slug>/<section>.md`. Use when several
  sibling research files share a parent theme (e.g. `core-ai-security`
  grouping `threats`, `defenses`, `frameworks`). Also auto-creates a
  `<major>/_index.md` hub that links the sibling sub-hubs.
- `--no-hierarchical` — force the flat single-file output even when the
  staged research has ≥ 5 sections.

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

## Hierarchical mode (multilevel research)

A staged research file with many sections (`## §1` / `## §2` / …
H2, or `### 1.` / `### 2.` / … H3) almost never maps to a single
leaf note — the sections are themselves the natural leaf-note
boundaries, and forcing them into one note makes a 1,000-line monster
that defeats Obsidian navigation.

`--hierarchical` (or the auto-enable rule of **≥ 5 numbered sections**)
splits the staged research into one leaf note per section, plus an
auto-generated sub-hub. With `--major <name>`, an extra directory
level is added so sibling research files can share a parent theme.

### When to use

Use hierarchical mode when:

- The staged research has ≥ 5 sections **and** each section is
  self-contained enough to stand alone as a leaf note (the typical
  case for 30-min+ research dossiers).
- Multiple sibling research files share a parent theme (e.g.
  `core-ai-security-threats`, `core-ai-security-defenses`,
  `core-ai-security-frameworks`). Group them under `--major
  core-ai-security` so the wiki gains a natural 3-level hierarchy.

Do **not** use hierarchical mode for:

- Free-text input with no staged research — there's nothing to split.
- A staged research with 1–3 sections — split or condense the source
  research instead; one section per leaf note is overkill.
- The user asked for a single named topic (e.g. "JWT pitfalls") — flat
  is right.

### File-path scheme

| Invocation | Per-section leaf path | Auto-generated hubs |
|---|---|---|
| `--hierarchical` (no `--major`) | `wiki/<domain>/<slug>/<section>.md` | `wiki/<domain>/<slug>/_index.md` (sub-hub) |
| `--hierarchical --major <m>` | `wiki/<domain>/<m>/<slug>/<section>.md` | `wiki/<domain>/<m>/<slug>/_index.md` (sub-hub) + `wiki/<domain>/<m>/_index.md` (major hub) |
| No flag, single-section research | `wiki/<domain>/<slug>.md` | (none) |

`<slug>` is the research filename without the `.md` extension. `<section>`
is a kebab-case derivative of the section heading (e.g. `## §3 Prompt
Injection` → `prompt-injection.md`). Use `_index.md` (with the
underscore prefix) for hub files so they sort to the top of any directory
listing — never number them with a `00-` prefix.

### Steps (when hierarchical kicks in)

1. **Parse the staged research into sections.** H2 sections with the
   `## §N` pattern, or H3 sections with the `### N.` pattern, are the
   leaf-note boundaries. The H2/H3 heading number is dropped from the
   filename; the heading text becomes the leaf-note H1.
2. **Determine the target directory** per the table above. The
   `<domain>` is still picked from `wiki-router.md` (e.g. the three
   `core-ai-security-*` research files all route to
   `ai-agent-wiki`). The `<slug>` is the staged filename without
   `.md`. The `<major>` is the explicit `--major` value, if any.
3. **Create the target directory tree** if it does not exist.
4. **For each parsed section**, build a leaf note following
   `_shared/note-schema.md`. Filename: kebab-case of the section
   heading, ≤ 60 chars, no leading number. Body: section content as
   written, plus a TL;DR distilled from the section's first
   non-heading, non-table paragraph.
5. **Auto-generate `<slug>/_index.md`** (the sub-hub): H1, one-line
   TL;DR, `## Leaf Notes` listing each per-section file with a
   `[[wikilink]]`, `## Source` linking back to the staged research,
   `## Related` pointing at the parent hub, the sibling sub-hubs
   (if `--major` is used), and the existing 00-index for the domain.
6. **Auto-generate `<major>/_index.md`** (the major hub) **only when
   `--major` is set**: H1, TL;DR, `## Sub-Domains` listing each
   `<slug>/_index.md` with a `[[wikilink]]`, `## Source Research`
   linking each staged file, `## Related` for cross-cutting siblings.
7. **Mark the staged file as promoted** with `promoted_to:
   wiki/<domain>/[<major>/]<slug>/_index.md` (the sub-hub, not any
   individual leaf note — the sub-hub is the durable entry point).
8. **Log the ingest** in `wiki/<domain>/log.md` with the leaf count
   and a one-line description, just like the flat path. The major
   hub's creation (if any) gets its own log entry.

### Back-link rules in hierarchical mode

Each per-section leaf note has the same `## Related` shape:

- `[[<slug>/_index.md|<Slug> sub-hub]]`
- `[[<major>/_index.md|<Major> hub]]` (when `--major` is set)
- Each sister `<other-slug>/_index.md` sub-hub (when `--major` is set)
- `[[<domain>/00-index.md|<Domain> index]]` (or whichever hub already
  exists for the domain)

This produces a dense mesh in Obsidian's graph view: per-section leaves
→ sub-hub → major hub → 00-index, with edges to all sibling sub-hubs.
No leaf note should be more than two hops from the domain index.

### Worked example

Three staged research files: `core-ai-security-threats.md`
(14 sections), `core-ai-security-defenses.md` (10 sections),
`core-ai-security-frameworks.md` (10 sections). Invocation:

```
/obsidian-organize:add_wiki core-ai-security-threats \
  --hierarchical --major core-ai-security --vault /Users/sanghee/dev/mywiki
/obsidian-organize:add_wiki core-ai-security-defenses \
  --hierarchical --major core-ai-security --vault /Users/sanghee/dev/mywiki
/obsidian-organize:add_wiki core-ai-security-frameworks \
  --hierarchical --major core-ai-security --vault /Users/sanghee/dev/mywiki
```

Produced tree (38 files total):

```
wiki/ai-agent-wiki/core-ai-security/
├── _index.md                                     (major hub)
├── threats/
│   ├── _index.md                                 (sub-hub)
│   ├── executive-summary.md                      (leaf)
│   ├── owasp-llm-top-10.md
│   ├── prompt-injection.md
│   ├── ...                                       (11 more)
├── defenses/
│   ├── _index.md
│   ├── guardrails.md
│   ├── ...                                       (9 more)
└── frameworks/
    ├── _index.md
    ├── nist-ai-rmf.md
    ├── ...                                       (9 more)
```

Staged files all get `promoted_to: wiki/ai-agent-wiki/core-ai-security/<slug>/_index.md` and `status: promoted`.

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
- Hierarchical mode + a staged research with **0 parseable sections**
  → refuse with a clear error; do not silently fall back to flat
  output.

## Cross-PR contract

The CLI behavior described in this SKILL.md is delivered by the
`obsidian-organize:add_wiki` Python implementation in
`../_lib/add_wiki.py` (PR #10). The skill above is the contract; the
implementation is the SSOT for argument parsing, slug derivation,
section splitting, and index-hub generation. When the two diverge:

- If the SKILL.md describes a flag the implementation does not yet
  honor → treat the SKILL.md as the spec; flag the gap in the PR
  thread; refuse to merge until implementation catches up.
- If the implementation supports a flag the SKILL.md does not describe
  → flag the gap; the SKILL.md MUST be updated before merging any
  implementation change, so users never see an undocumented flag.
- Flag interactions live in the SKILL.md (--hierarchical +
  --major; --hierarchical auto-enable at ≥ 5 sections). The
  implementation MUST follow the auto-enable rule exactly — flipping
  the threshold is a behavior change, not a bug fix.

The two PRs (this one + the implementation PR) must merge together or
not at all. A partial merge leaves the skill describing features that
do not exist (or vice versa) and breaks `obsidian-organize:bootstrap`
consumers.

## Troubleshooting

Symptoms a user might see, the most likely cause, and the right
recovery action. Use this when something "didn't work" but the
output doesn't point at a specific step:

- **`--hierarchical` ignored on a clearly multi-section input.** The
  auto-enable rule requires **≥ 5 numbered sections** AND the section
  pattern to be `## §N …` or `### N. …`. Mixed styles, descriptive
  headings, or fewer than 5 sections disable the auto-enable. Recovery:
  re-number the headings to match the pattern, or pass `--hierarchical`
  explicitly to force-enable.
- **Sibling research files land in separate top-level dirs.** The
  `--major` flag was not passed on the second/third invocations, so
  each file got its own auto-generated major. Recovery: re-run with the
  same `--major <name>` on every sibling so the major hub links them.
  The hub can be hand-edited to merge in pre-existing siblings.
- **`--no-backlinks` did not skip Related on the new leaf.** The
  implementation always writes the leaf's `## Related`; `--no-backlinks`
  only skips the *reverse* pass that touches existing siblings. This is
  by design — a leaf with no `## Related` is an isolated node.
- **`gh` auth failure in `--mode=super`.** Stop, surface the gh
  unauthenticated state, do not silently fall back to `--mode=single`.
  The user must re-auth or accept a `--mode=single` run explicitly.
- **Auto-enable kicked in for a 3-section research.** Bug — the
  threshold is 5, not 3. File an issue with the section count + the
  output path. Do not edit the leaf by hand; the implementation is
  the SSOT and a one-off rename pollutes the graph.
- **Vault root cannot be inferred.** `obsidian-organize:bootstrap`
  MUST be run before `add_wiki`; without it the vault root is unknown
  and the skill refuses. Recovery: invoke bootstrap first, then retry.

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

## Examples

Flat (single leaf):

```
/obsidian-organize:add_wiki JWT security pitfalls --mode=single --dry-run
```

Hierarchical, sibling-grouped under a major theme:

```
/obsidian-organize:add_wiki _research/core-ai-security-threats.md \
  --mode=single --hierarchical --major core-ai-security
```

This writes per-section leaf notes under
`wiki/core-ai-security/threats/<section>.md` plus a
`<threats>/_index.md` sub-hub and a `<core-ai-security>/_index.md`
parent hub linking the sibling sub-hubs.
