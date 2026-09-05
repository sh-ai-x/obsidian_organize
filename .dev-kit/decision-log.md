# Decision log — /dev-kit:plan

## Gate 0 — Interview consume

- `--skip-interview` flag present → SKIPPED (interview consume gate bypassed; audit trail per skill rules).
- Phase: `obsidian-topic-organizer`
- Branch base: `plan/obsidian-topic-organizer`
- Brief: "Obsidian topic-organizer plugin with research/add_wiki/remove_wiki skills, referencing hermes-wiki-super"

## Gate 1 — frame

- **goal**: Ship a Claude Code plugin that organizes an Obsidian vault by topic, exposing three skills — research (gather source material), add_wiki (promote to topic note), remove_wiki (withdraw topic + staged inputs) — with frontmatter + tag conventions inherited from hermes-wiki-super's add-wiki / process-clippings skills.
- **target user**: Solo PKM practitioner — one developer maintaining their own Obsidian vault; runs Claude Code locally; values reproducibility of the topic-organize workflow over collaborative features.
- **situation**: The user runs add-wiki and process-clippings skills manually against `~/Documents/Obsidian Vault/hermes-wiki-super`; topic structure exists but no first-class research/add_wiki/remove_wiki workflow.

## Gate 2 — validate

### 2.1 Evidence (3 signals)

| # | Origin | Source | Claim | Date |
|---|---|---|---|---|
| 1 | existing vault workflow | `~/Documents/Obsidian Vault/hermes-wiki-super/add-wiki` skill | A manual topic-note workflow already exists; plugin formalizes it. | 2026-09-05 |
| 2 | existing vault workflow (distinct artifact) | `~/Documents/Obsidian Vault/hermes-wiki-super/process-clippings` skill | Staged-input handling is already a concept; `research` maps onto its output. | 2026-09-05 |
| 3 | parent-repo convention (analogue) | `dev-harness-kit` plugin in same parent repo | Plugin follows `namespace:skill` naming (e.g. `obsidian-organize:research`); additive over existing skills, not replacement. | 2026-09-05 |

### 2.2 Value score — best-effort

- LTV_per_user: $0 (personal dogfood)
- reachable_users_year1: 1 (operator only)
- total_cost: $0 (sunk personal time)
- value_score: undefined (0/0)
- Decision: **best-effort**. Operator directed proceed: "개인 생산성을 위한것이니 그냥 진행" (personal productivity, just proceed). Formula's commercial-value premise doesn't match the personal-dogfood use case. Build stage inherits the best-effort acknowledgment.

### 2.3 Ambiguity loop — skipped (best-effort gate short-circuits convergence test)

### 2.4 Convergence test — PASS (best-effort overrides value_score dimension)

### 2.5 Constraints captured for Gate 4 / Gate 5

- **Naming**: `namespace:skill` convention (per `dev-harness-kit` analogue). Recommended plugin namespace: `obsidian-organize`. Skill IDs: `obsidian-organize:research`, `obsidian-organize:add_wiki`, `obsidian-organize:remove_wiki`.
- **Additive design**: extend the existing `add-wiki` and `process-clippings` skills in `hermes-wiki-super`; do not replace them. The plugin's skills sit one layer above — `research` produces staged input that `add-wiki` would have produced by hand; `add_wiki` formalizes promotion into a topic note; `remove_wiki` retires it.

## Gate 3 — non-goals

| # | Non-goal | Rationale | Breach-response |
|---|---|---|---|
| 1 | No bidirectional Obsidian sync (mobile/cloud). | Plugin operates on the local vault; remote sync is Obsidian's job. Different problem space. | Defer to Obsidian Sync; if reviewer pushes, point to the product boundary. |
| 2 | No migration tooling for pre-existing topic notes. | Plugin handles notes created via its own skills; legacy notes are left as-is. Migration is one-shot; not a runtime concern. | Write a one-off script on request; don't bake it into the plugin. |
| 3 | No LLM-judge evaluation harness for plugin outputs. | Covered separately by `/dev-kit:evaluate`. Harness is project-level, not plugin-level. | Add per-skill unit + integration tests in the plugin itself; defer quality scoring to dev-kit's harness. |

## Gate 4 — decompose

- Phase directory: `phases/obsidian-topic-organizer/`
- Worktree branch base: `plan/obsidian-topic-organizer`
- 5 steps, dependency-first ordering: scaffold → research → add_wiki → remove_wiki → fixtures+tests

## Gate 5 — emit

Artifacts written:

- `PRD.md` — 6 sections (Frame, Validate, Non-goals, Phase plan, AC, Hand-off)
- `phases/obsidian-topic-organizer/index.json` — phase state machine
- `phases/obsidian-topic-organizer/step0.md` … `step4.md` — per-step preambles
- `.dev-kit/hand-off/plan→build.md` — build hand-off summary
- `.dev-kit/loop-log.json` — gate-by-gate cycle log
- `docs/proposals/plugins/obsidian-topic-organizer.yaml` — proposal source (legacy flat layout)
- `docs/proposals/review/plugins/obsidian-topic-organizer.yaml` — proposal source (status-routed bucket; design-discussion → review)
- `docs/proposals/review/plugins/obsidian-topic-organizer.html` — self-contained HTML (Bash was disabled, so canonical `python3 -m lib.render_proposal_html` could not run; HTML written directly. Operator can re-render with the CLI for the canonical CSS.)

## Bash disabled mid-plan

The plan skill body declares `disallowed-tools: Bash`. After loading, Bash became unavailable in this session. Commit could not be performed inside the skill execution. **Operator action required**: commit the plan artifacts from the worktree using a normal (non-plan) shell session.

## Final status

- Gate 0: SKIPPED (flag)
- Gate 1: captured (3 fields)
- Gate 2: PASS (best-effort value_score)
- Gate 3: captured (3 non-goals)
- Gate 4: emitted (5 steps + index.json)
- Gate 5: emitted (PRD + phases + proposal)
- Operator override: value_score → best-effort
- Next invocation: `/dev-kit:build obsidian-topic-organizer` (after operator commits artifacts to `plan/obsidian-topic-organizer`)
