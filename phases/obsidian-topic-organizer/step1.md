<!-- status: completed -->
<!-- ac: AC-2 -->
<!-- exit_code: 0 -->
<!-- duration_seconds: 0.004205 -->

# step 1 — research skill

## Status
pending

## Read first
- `~/Documents/Obsidian Vault/hermes-wiki-super/process-clippings` (output contract)
- `PRD.md` §3 (non-goals), §5 (AC)
- `.dev-kit/decision-log.md` §2.5 (constraints)

## Task
Implement `plugins/obsidian-organize/skills/research/` — the staged-input producer:

- `SKILL.md` — describes when to invoke (`/obsidian-organize:research <topic>`), inputs (a topic string + optional source URLs / file paths), outputs (a markdown file under `<vault>/_research/<topic>.md` with frontmatter `topic`, `created`, `sources[]`, `status: staged`).
- `references/output-schema.md` — canonical frontmatter + body shape; pinned so step 2 (`add_wiki`) can read it.

The skill reads from the existing `process-clippings` output convention in `hermes-wiki-super` and emits a topic-staged file that `add_wiki` will consume.

## Acceptance Criteria
- `plugins/obsidian-organize/skills/research/SKILL.md` is non-empty and documents: name, invocation, inputs, outputs, edge cases.
- `plugins/obsidian-organize/skills/research/references/output-schema.md` defines the frontmatter keys (`topic`, `created`, `sources`, `status`) with a worked example.
- A dry-run invocation (no actual vault write) on a fixture topic produces a string that matches `output-schema.md` (verified in step 4).

## Verification & Status Update
Run from repo root:

```bash
test -f plugins/obsidian-organize/skills/research/SKILL.md && echo "SKILL.md OK"
test -f plugins/obsidian-organize/skills/research/references/output-schema.md && echo "schema OK"
```

Update marker: `completed` on success, `error` + error_message on failure, `blocked` + blocked_reason on inability to proceed.

## Don't
- Don't write to the real `~/Documents/Obsidian Vault/hermes-wiki-super` vault — fixtures land under `plugins/obsidian-organize/tests/fixtures/vault/` in step 4.
- Don't invent a new frontmatter taxonomy; inherit from `process-clippings`.
- Don't add network calls (LLM or HTTP) inside this step — fixture tests in step 4 verify the contract with synthetic input.
