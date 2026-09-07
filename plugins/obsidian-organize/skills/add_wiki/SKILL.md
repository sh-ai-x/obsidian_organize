---
name: obsidian-organize:add_wiki
description: Promote a staged research file into a topic note — locally in one repo (--mode=single) or into the matching mybotagent/hermes-wiki-super sub-repo (--mode=super). Use when a topic's research is complete and you want a durable, navigable entry point.
---

# obsidian-organize:add_wiki

## What it does

Reads a staged research file at `<vault>/_research/<topic>.md` and writes a
topic note at `<vault>/topics/<topic>.md`. The topic note carries the topic's
sources as `[[wikilink]]` back-references and updates the staged file's
`status` to `promoted`.

## Invocation

```
/obsidian-organize:add_wiki <topic-or-file> [--mode=super|single] [--force] [--no-backlinks]
```

- `<topic-or-file>` is either a topic slug (e.g. `hermes-protocol`) or the
  direct path to a staged research file.
- `--mode=super|single` — pick the target explicitly; autodetected when omitted.
- `--force` — overwrite an existing topic note (default: refuse).
- `--no-backlinks` — skip the reverse-wikilink pass (useful for dry runs).

## Two modes

- **`--mode=super`** — each knowledge domain is its own GitHub repo under
  `mybotagent/`, mounted as a submodule under `wiki/`. **Read
  `../_shared/hermes-super.md` first** and follow it for sub-repo resolution,
  the LLM-Wiki page format, the two-level commit, and new-repo creation.
- **`--mode=single`** — the staged file is promoted to a local
  `topics/<topic>.md` in this one repo, per the Behavior section below.

When no `--mode` is given, autodetect and **state the detected mode in the
output** so the choice is never silent. Detection has three outcomes, not two —
`ambiguous` must not collapse into `single`, or the skill would silently pick a
mode in exactly the cases that warrant asking:

```bash
if [ ! -e .gitmodules ]; then
  echo single                        # no submodules at all -> one repo
elif ! grep -q 'submodule "' .gitmodules 2>/dev/null; then
  echo ambiguous                     # unreadable or unparseable -> ask
elif grep -q 'submodule "wiki/' .gitmodules; then
  echo super                         # wiki/ submodules -> constellation
else
  echo ambiguous                     # submodules, but none under wiki/ -> ask
fi
```

On `ambiguous`, stop and ask: say what was found (which submodules, or that
`.gitmodules` could not be read) and which mode you propose. Never resolve an
`ambiguous` result by falling through to a default.

An explicit `--mode` always wins over autodetection and skips this check
entirely. `--mode=single` inside a super-repo clone is legitimate — it keeps a
topic local instead of publishing it to its own repo.

`--local` is accepted as a deprecated alias for `--mode=single`.

## Behavior — `--mode=super`

1. Resolve the staged file: `<vault>/_research/<topic>.md`. Fail if missing.
2. Resolve which existing sub-repo owns the domain, reading `.gitmodules`,
   `wiki-map.md`, and the sub-repos' `*-hub.md` files. Prefer an existing
   domain — a facet of a covered domain becomes a page inside it, not a new
   repo. Only create a repo when nothing covers it, and say which and why
   first.
3. Write the promoted note as an LLM-Wiki **content page** inside that
   sub-repo: `tags` / `related` / `source` frontmatter, a one-line summary
   blockquote, then the staged body's `## Notes` as the article, and the
   staged `sources[]` as a `## Sources` section.
4. Add a `[[wikilink]]` row to that sub-repo's hub under the fitting section,
   and bump the hub's `Last updated:`. Skip if a row for the page already
   exists, so re-runs do not duplicate rows.
5. Commit and push **inside the submodule**, then bump the pointer in the super
   repo — or run the super repo's `sync.sh`.
6. Only after the push succeeds, update the staged file's frontmatter:
   `status: promoted`, `promoted_to: <owner>/<repo>#<path>`,
   `updated: <ISO-8601>`. Marking it promoted before the push would strand the
   research with nothing published.

## Behavior — `--mode=single`

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

- `../_shared/hermes-super.md` — sub-repo resolution, LLM-Wiki format,
  two-level commit, new-repo creation.
- `references/frontmatter.md` — canonical topic-note frontmatter (`--mode=single`).
- `obsidian-organize:research` — produces the staged input.
- `obsidian-organize:process_clippings` — the other writer into the same
  sub-repos; in `--mode=single` it owns `wiki/` and `wiki-map.md`.
- `obsidian-organize:remove_wiki` — retires a topic note.
