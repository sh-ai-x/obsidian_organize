# Wiki router

Decide which `wiki/<domain>/` directory a new leaf note belongs in.
Reference: `/Users/sanghee/Documents/Obsidian Vault/hermes-wiki-super/wiki/`
contents as of 2026-09-07.

## Existing domains

These are the wikis currently in the super-repo. Match the topic of the
new note against the descriptions. If nothing fits, see "New wiki" below.

| Domain | Path | What goes here |
|---|---|---|
| `ai-agent-wiki` | `wiki/ai-agent-wiki/` | AI agent architecture, RAG, multi-agent, MCP/A2A, agent security, agentic tooling, agent stacks |
| `ai-job-analysis` | `wiki/ai-job-analysis/` | AI hiring market, blue-ocean roles, career analysis, salary data |
| `ai-marketing-wiki` | `wiki/ai-marketing-wiki/` | AI marketing, SEO/AEO/GEO, agency playbooks, content strategy |
| `harness-engineering-wiki` | `wiki/harness-engineering-wiki/` | Harness engineering, instruction files (CLAUDE.md/AGENTS.md), context rot, permissions, delegation, MCP, skills, hooks, workflows |
| `hermes-logs` | `wiki/hermes-logs/` | Timestamped change logs, agent traces, run history |
| `hermes-prompts` | `wiki/hermes-prompts/` | Reusable system prompts, copywriting, translation, business prompts |
| `hermes-slash-commands` | `wiki/hermes-slash-commands/` | Slash command reference, command authoring |
| `hermes-wiki` | `wiki/hermes-wiki/` | General Hermes knowledge, solopreneur, repos, infra, people, watchlist |
| `hermes-wiki-claude-code` | `wiki/hermes-wiki-claude-code/` | Claude Code specifics — CLI modes, hooks, MCP, skills, sessions, plugins |
| `hermes-wiki-codex` | `wiki/hermes-wiki-codex/` | Codex CLI, command reference, comparison vs Claude Code |
| `hermes-wiki-quant` | `wiki/hermes-wiki-quant/` | Quantitative trading, stock analysis, macro indicators |
| `hermes-wiki-schedule` | `wiki/hermes-wiki-schedule/` | Scheduling, routines, calendar integration |
| `subagents-library` | `wiki/subagents-library/` | Sub-agent patterns, multi-agent designs |

## Routing decision process

1. **Skim the existing `<domain>/index.md` or `<domain>/<hub>.md`** for
   the top 2–3 candidate domains. Note the existing tags and the
   filenames — they tell you the keyword vocabulary the domain uses.
2. **Test the topic against the table above** using these cues:
   - Subject is *about AI agents* (architecture, patterns, security) →
     `ai-agent-wiki`.
   - Subject is *about Claude Code specifically* (CLI, settings, hooks,
     MCP servers, plugins) → `hermes-wiki-claude-code`.
   - Subject is *about Codex or its CLI* → `hermes-wiki-codex`.
   - Subject is *about how to design the harness around an agent*
     (permissions, context management, instruction files, workflows) →
     `harness-engineering-wiki`.
   - Subject is a *timestamped event* (an incident, a run, a fix) →
     `hermes-logs`.
3. **If two domains both match**, prefer the more specific one. Example:
   "Strix" is in `ai-agent-wiki/18-strix.md` (agent topic), not
   `harness-engineering-wiki/` (which is about designing the harness,
   not testing it).
4. **If nothing matches**, see "New wiki" below.

## New wiki

Create a new `<domain>` when:

- The topic is a coherent knowledge area not covered by the existing
  domains.
- The new wiki will accumulate ≥ 5 notes over time — a 1-note "wiki"
  is a folder, not a wiki.
- The name is short, kebab-case, and uses the same vocabulary as the
  other domains (e.g. `ai-finance-wiki`, not `finance-notes`).

When creating a new wiki:

- Add the directory under `wiki/<domain>/` with an `index.md` (master
  catalog) and a `log.md` (change history).
- Append a top-level section to the vault root `wiki-map.md` with a
  `[[wikilinks]]` pointer to the new domain.
- Add the new domain to the table above (in this file) on the next
  plugin release so future routing uses it.

## Updating existing notes

When a new note is closely related to an existing one in the same
domain (e.g. this clipping extends `ai-agent-wiki/18-strix.md` with the
context-aware-pentesting launch), the right move is to **add a new
note in the same domain** with `related:` pointing to the existing one
and a `## Related` bullet back. Do not edit the existing note in
place unless the new content is a clear correction — wikis grow by
accumulation, not by rewriting.

## Worked routing examples

| Input | Routed to | Reason |
|---|---|---|
| Clipping about Strix context-aware pentesting | `ai-agent-wiki/19-context-aware-pentesting.md` | AI agent + security testing; sibling of `18-strix.md` |
| Clipping about a run of `claude-code -p` that timed out | `hermes-logs/2026-09-07-claude-timeout.md` | Timestamped incident, not architectural |
| Clipping about new Codex CLI flag | `hermes-wiki-codex/configuration/codex-cli-flag.md` | Codex-specific config |
| Clipping about AppSec 2026 trends (OWASP, supply chain) | `harness-engineering-wiki/security/appsec-2026.md` | AppSec sits in the harness-engineering security subtree |
| Free-text: "Write me a note on JWT security" | `harness-engineering-wiki/security/jwt-security.md` | Cross-cutting security concept; security/ subdir already exists in that domain |
| Free-text: "Add the AI Pentest tool PentAGI" | `ai-agent-wiki/20-pentagi.md` | AI agent + pentest, sibling of Strix |
