<!-- status: completed -->
<!-- ac: AC-4 -->
<!-- exit_code: 0 -->
<!-- duration_seconds: 0.004256 -->

# step 3 — remove_wiki skill

## Status
pending

## Read first
- `plugins/obsidian-organize/skills/add_wiki/references/frontmatter.md` (topic-note schema from step 2)
- `plugins/obsidian-organize/skills/research/references/output-schema.md` (staged-input schema from step 1)
- `PRD.md` §3 (non-goals)

## Task
Implement `plugins/obsidian-organize/skills/remove_wiki/` — retire a topic note and its staged inputs:

- `SKILL.md` — invocation `/obsidian-organize:remove_wiki <topic>`. Identifies the topic note by `topic:` frontmatter key, removes the `[[wikilink]]` entries from sources (sources keep their content; just drop the back-link to the removed topic), archives the staged research file (move to `<vault>/_archive/research/<topic>-<timestamp>.md`), and deletes the topic note. Dry-run mode prints the planned mutations and exits 0 without writing.
- `references/cleanup-rules.md` — defines: which files to scan for back-links (recursive in `<vault>`), how to handle missing files, archive path naming convention.

Additive: does not touch any non-topic, non-staged files.

## Acceptance Criteria
- `plugins/obsidian-organize/skills/remove_wiki/SKILL.md` is non-empty and documents: name, invocation, inputs, outputs, dry-run flag, edge cases (topic note missing → fail; staged file missing → continue with warning).
- `plugins/obsidian-organize/skills/remove_wiki/references/cleanup-rules.md` lists the scan-root, archive path, and back-link removal algorithm.
- Dry-run mode (`--dry-run`) does not modify any file (verified in step 4).

## Verification & Status Update
Run from repo root:

```bash
test -f plugins/obsidian-organize/skills/remove_wiki/SKILL.md && echo "SKILL.md OK"
test -f plugins/obsidian-organize/skills/remove_wiki/references/cleanup-rules.md && echo "rules OK"
```

Update marker: `completed` on success, `error` + error_message on failure, `blocked` + blocked_reason on inability to proceed.

## Don't
- Don't delete non-topic, non-staged files; the scan-root is restricted to `_research/`, `topics/`, and source-file back-links.
- Don't merge with the existing `hermes-wiki-super/add-wiki` skill — `remove_wiki` is its own concern.
- Don't reproduce the existing vault's notes by migration (per non-goal 2).
