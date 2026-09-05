# PRD — Obsidian topic-organizer plugin

Phase: `obsidian-topic-organizer`
Branch: `plan/obsidian-topic-organizer`
Issue: [#2](https://github.com/sh-ai-x/obsidian_organize/issues/2)
Date: 2026-09-05
Status: design-discussion

---

## §1 — Frame

- **goal**: Ship a Claude Code plugin that organizes an Obsidian vault by topic, exposing three skills — research (gather source material), add_wiki (promote to topic note), remove_wiki (withdraw topic + staged inputs) — with frontmatter + tag conventions inherited from hermes-wiki-super's add-wiki / process-clippings skills.
- **target user**: Solo PKM practitioner — one developer maintaining their own Obsidian vault; runs Claude Code locally; values reproducibility of the topic-organize workflow over collaborative features.
- **situation**: The user runs add-wiki and process-clippings skills manually against `~/Documents/Obsidian Vault/hermes-wiki-super`; topic structure exists but no first-class research/add_wiki/remove_wiki workflow.

---

## §2 — Validate

| Dimension | Result |
|---|---|
| Evidence | **3 sources** (vault add-wiki, vault process-clippings, dev-harness-kit namespace convention) |
| Value score | **best-effort** (personal dogfood: LTV=$0, users=1, cost=$0; formula's commercial-value premise doesn't match) |
| Ambiguity | loop skipped (best-effort gate short-circuits convergence test) |
| Convergence | **PASS** (best-effort overrides value_score dimension) |

Per `.dev-kit/decision-log.md` Gate 2.5: naming follows `namespace:skill` (e.g. `obsidian-organize:research`); the plugin is additive over the existing `hermes-wiki-super` skills, not a replacement.

---

## §3 — Non-goals

| # | Non-goal | Rationale | Breach-response |
|---|---|---|---|
| 1 | No bidirectional Obsidian sync (mobile/cloud). | Plugin operates on the local vault; remote sync is Obsidian's job. Different problem space. | Defer to Obsidian Sync; if reviewer pushes, point to the product boundary. |
| 2 | No migration tooling for pre-existing topic notes. | Plugin handles notes created via its own skills; legacy notes are left as-is. Migration is one-shot; not a runtime concern. | Write a one-off script on request; don't bake it into the plugin. |
| 3 | No LLM-judge evaluation harness for plugin outputs. | Covered separately by `/dev-kit:evaluate`. Harness is project-level, not plugin-level. | Add per-skill unit + integration tests in the plugin itself; defer quality scoring to dev-kit's harness. |

---

## §4 — Phase plan

- Phase state machine: `phases/obsidian-topic-organizer/index.json`
- Per-step preambles: `phases/obsidian-topic-organizer/step<N>.md` (N=0..4)
- Step ordering is dependency-first.

| Step | Title | Depends on |
|---|---|---|
| 0 | Plugin scaffold + manifest | — |
| 1 | research skill | 0 |
| 2 | add_wiki skill | 0, 1 |
| 3 | remove_wiki skill | 0, 2 |
| 4 | Vault fixture + per-skill tests + integration test | 1, 2, 3 |

---

## §5 — Acceptance criteria (1:1 with step AC commands)

| AC | Step | Command |
|---|---|---|
| AC-1: plugin manifest exists and lists three skills | 0 | `jq . plugins/obsidian-organize/.claude-plugin/plugin.json` |
| AC-2: research skill + output schema | 1 | `test -f plugins/obsidian-organize/skills/research/{SKILL.md,references/output-schema.md}` |
| AC-3: add_wiki skill + frontmatter schema | 2 | `test -f plugins/obsidian-organize/skills/add_wiki/{SKILL.md,references/frontmatter.md}` |
| AC-4: remove_wiki skill + cleanup rules | 3 | `test -f plugins/obsidian-organize/skills/remove_wiki/{SKILL.md,references/cleanup-rules.md}` |
| AC-5: integration test exits 0 | 4 | `pytest plugins/obsidian-organize/tests/ -v` |

---

## §6 — Hand-off

- **Review artifact**: `/dev-kit:proposal plugins/obsidian-topic-organizer` (auto-rendered to `docs/proposals/plugins/obsidian-topic-organizer.html`)
- **Next stage**: `/dev-kit:build obsidian-topic-organizer` — reads `phases/obsidian-topic-organizer/index.json` + per-step preambles and runs the harness-runner.
- **Review chain**: `/dev-kit:review` (3-dim) → `/dev-kit:security` (10-dim) → `/dev-kit:ship`.
