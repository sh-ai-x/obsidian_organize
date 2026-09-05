<!-- status: completed -->
<!-- ac: AC-3 -->
<!-- exit_code: 0 -->
<!-- duration_seconds: 0.004034 -->

# step 2 — add_wiki skill

## Status
pending

## Read first
- `~/Documents/Obsidian Vault/hermes-wiki-super/add-wiki` (existing manual skill — additive, not replacement)
- `plugins/obsidian-organize/skills/research/references/output-schema.md` (input contract from step 1)
- `PRD.md` §5 (AC)

## Task
Implement `plugins/obsidian-organize/skills/add_wiki/` — promote a staged research file into a topic note:

- `SKILL.md` — invocation `/obsidian-organize:add_wiki <topic-or-file>`. Reads a staged file from `_research/<topic>.md`, writes a topic note at `<vault>/topics/<topic>.md` with frontmatter `topic`, `created`, `updated`, `tags[]`, `sources[]`, `status: active`. Adds an Obsidian `[[wikilink]]` from each source file back to the new topic note.
- `references/frontmatter.md` — canonical topic-note frontmatter; pinned so step 3 (`remove_wiki`) can match on it.

Additive design: this skill sits one layer above the existing `add-wiki` skill. The existing skill stays untouched; `add_wiki` either delegates to it (for the promotion) or runs the equivalent logic on the staged file.

## Acceptance Criteria
- `plugins/obsidian-organize/skills/add_wiki/SKILL.md` is non-empty and documents: name, invocation, inputs (staged research file), outputs (topic note + reverse wikilinks), edge cases (staged file missing → fail with clear message; topic note already exists → refuse to overwrite unless `--force`).
- `plugins/obsidian-organize/skills/add_wiki/references/frontmatter.md` defines the topic-note frontmatter schema.
- The skill does NOT mutate the staged research file (it copies/reads; the staged file is consumed by remove_wiki or archived).

## Verification & Status Update
Run from repo root:

```bash
test -f plugins/obsidian-organize/skills/add_wiki/SKILL.md && echo "SKILL.md OK"
test -f plugins/obsidian-organize/skills/add_wiki/references/frontmatter.md && echo "schema OK"
```

Update marker: `completed` on success, `error` + error_message on failure, `blocked` + blocked_reason on inability to proceed.

## Don't
- Don't replace the existing `hermes-wiki-super/add-wiki` skill. The plugin delegates or wraps; it does not shadow.
- Don't delete staged research files in this step — that's `remove_wiki`'s concern.
- Don't write bidirectional sync (per non-goal 1).
