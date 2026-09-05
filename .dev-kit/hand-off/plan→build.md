# plan → build hand-off

## Plan
- Phase: `obsidian-topic-organizer`
- Branch base: `plan/obsidian-topic-organizer`
- PRD: `PRD.md`
- Phase JSON: `phases/obsidian-topic-organizer/index.json`
- Steps: `phases/obsidian-topic-organizer/step{0..4}.md`

## Step summary (5 steps, dependency-first)

| # | Name | Status | Depends on | AC |
|---|---|---|---|---|
| 0 | scaffold | pending | — | AC-1: plugin manifest exists and lists three skills |
| 1 | research-skill | pending | 0 | AC-2: research skill + output schema |
| 2 | add-wiki-skill | pending | 0, 1 | AC-3: add_wiki skill + frontmatter schema |
| 3 | remove-wiki-skill | pending | 0, 2 | AC-4: remove_wiki skill + cleanup rules |
| 4 | fixtures-and-tests | pending | 1, 2, 3 | AC-5: integration test exits 0 |

## Design constraints (from decision-log §2.5)

- **Naming**: `namespace:skill` convention. Skill IDs: `obsidian-organize:research`, `obsidian-organize:add_wiki`, `obsidian-organize:remove_wiki`.
- **Additive design**: extend the existing `add-wiki` and `process-clippings` skills in `hermes-wiki-super`; do not replace them.

## Review artifact

- `/dev-kit:proposal plugins/obsidian-topic-organizer` → `docs/proposals/plugins/obsidian-topic-organizer.html`

## Next invocation

```
/dev-kit:build obsidian-topic-organizer
```

The build runner reads `phases/obsidian-topic-organizer/index.json` and per-step preambles, then executes via harness-runner with one sub-agent per step (MUST-36), 3-cycle self-fix guard (MUST-37), per-step worktree isolation (MUST-38), and the 2-commit protocol on per-step branches `<branch-base>-step<N>`.

## Operator overrides

- Gate 2.2 (value_score) marked **best-effort** — operator note: "개인 생산성을 위한것이니 그냥 진행".
