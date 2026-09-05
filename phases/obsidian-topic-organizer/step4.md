<!-- status: completed -->
<!-- ac: AC-5 -->
<!-- exit_code: 0 -->
<!-- duration_seconds: 2.18682 -->
<!-- tests_passed: 16 -->

# step 4 — Vault fixture + per-skill tests + integration test

## Status
pending

## Read first
- `plugins/obsidian-organize/skills/research/references/output-schema.md`
- `plugins/obsidian-organize/skills/add_wiki/references/frontmatter.md`
- `plugins/obsidian-organize/skills/remove_wiki/references/cleanup-rules.md`
- `PRD.md` §5 (AC list)

## Task
Add fixtures and tests so the plugin is verifiable end-to-end on a synthetic vault:

- `plugins/obsidian-organize/tests/fixtures/vault/` — minimal vault with `_research/`, `topics/`, and a handful of `sources/` markdown files.
- `plugins/obsidian-organize/tests/test_research.py` — drives `research` skill on a fixture topic, asserts output file + frontmatter shape.
- `plugins/obsidian-organize/tests/test_add_wiki.py` — drives `add_wiki` on the fixture staged file, asserts topic note creation + reverse wikilinks.
- `plugins/obsidian-organize/tests/test_remove_wiki.py` — drives `remove_wiki --dry-run` first, then `--apply`, asserts topic note deletion + back-link removal + staged-file archive.
- `plugins/obsidian-organize/tests/test_integration.py` — chains research → add_wiki → remove_wiki on one topic; asserts vault state matches expected post-conditions.

Tests use the existing `scripts/test.sh` runner or `pytest` (whichever is canonical in this repo).

## Acceptance Criteria
- `pytest plugins/obsidian-organize/tests/` exits 0 with all tests passing.
- The integration test verifies the full lifecycle: research creates staged file → add_wiki creates topic note + back-links → remove_wiki archives staged file + removes back-links + deletes topic note.
- Each per-skill test asserts at least one frontmatter key and one body link, so the schema is regression-protected.
- Test fixture vault is hermetic: no writes to the real `~/Documents/Obsidian Vault/hermes-wiki-super`.

## Verification & Status Update
Run from repo root:

```bash
pytest plugins/obsidian-organize/tests/ -v
```

Update marker: `completed` on success, `error` + error_message on failure, `blocked` + blocked_reason on inability to proceed.

## Don't
- Don't write to the real `~/Documents/Obsidian Vault/hermes-wiki-super`; tests use `tests/fixtures/vault/` only.
- Don't add LLM-judge scoring here (per non-goal 3); stick to deterministic assertions.
- Don't pull in `dev-harness-kit` runtime — tests are plugin-internal.
