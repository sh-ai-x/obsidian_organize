<!-- status: completed -->
<!-- ac: AC-1 -->
<!-- exit_code: 0 -->
<!-- duration_seconds: 0.010879 -->

# step 0 — Plugin scaffold + manifest

## Status
pending

## Read first
- `PRD.md` §1, §4, §5
- `.dev-kit/decision-log.md` Gate 4 (decompose)
- `docs/proposals/obsidian-topic-organizer/obsidian-topic-organizer.html` (auto-rendered)

## Task
Create the plugin skeleton under `plugins/obsidian-organize/` with the `namespace:skill` convention inherited from `dev-harness-kit`:

- `plugins/obsidian-organize/.claude-plugin/plugin.json` — declares plugin namespace `obsidian-organize`, lists three skills (`research`, `add_wiki`, `remove_wiki`) by relative path under `skills/<skill-name>/SKILL.md`.
- `plugins/obsidian-organize/skills/.keep` — empty marker; per-skill directories are created in steps 1–3.
- `plugins/obsidian-organize/README.md` — short plugin description, three skill IDs, link to PRD §5 AC.

Manifest fields follow the `dev-harness-kit` analogue: `name`, `version`, `description`, `skills[]`, `authors[]`, `license`.

## Acceptance Criteria
- `cat plugins/obsidian-organize/.claude-plugin/plugin.json` parses as JSON and lists three skill entries pointing at `skills/research/SKILL.md`, `skills/add_wiki/SKILL.md`, `skills/remove_wiki/SKILL.md`.
- `plugins/obsidian-organize/README.md` documents the plugin name, the three skill IDs in `namespace:skill` form, and links to PRD §5.
- `ls plugins/obsidian-organize/skills/` succeeds (the directory exists, even if it currently only holds `.keep`).

## Verification & Status Update
Run from repo root:

```bash
jq . plugins/obsidian-organize/.claude-plugin/plugin.json | head -20
test -f plugins/obsidian-organize/README.md && echo "README OK"
```

Update the marker to `<!-- status: completed -->` on success, `<!-- status: error -->` + error_message on failure, `<!-- status: blocked -->` + blocked_reason on inability to proceed.

## Don't
- Don't write any per-skill content in this step (research/add_wiki/remove_wiki land in steps 1–3).
- Don't add CI / `.github/workflows/` changes (those belong to the repo-level scaffolding, not the plugin).
- Don't import or depend on `dev-harness-kit`'s runtime; the plugin is self-contained under its own namespace.
