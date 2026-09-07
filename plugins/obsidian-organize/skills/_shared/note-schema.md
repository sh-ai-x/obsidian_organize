# LLM-Wiki note schema

Canonical frontmatter + body shape for every leaf note written by
`process_clippings` and `add_wiki`. Derived from the
`hermes-wiki-super/wiki/ai-agent-wiki/` convention, which is the source of
truth for Obsidian graph quality in this vault.

## File path

```
<vault>/wiki/<domain>/<note>.md
```

For hierarchical layouts (a staged research split into per-section
leaf notes with auto-generated sub-hubs), see `add_wiki` § Hierarchical
mode. The path becomes:

```
<vault>/wiki/<domain>/<slug>/<section>.md              # with --hierarchical
<vault>/wiki/<domain>/<major>/<slug>/<section>.md     # with --major
```

- `<domain>` is a top-level knowledge area (see `wiki-router.md`).
- `<note>` is a kebab-case filename. If a domain uses numbered pages
  (`00-index`, `01-llm-hallucination`), continue the sequence; otherwise
  use a content-derived name.
- Hub files are always named `_index.md` (underscore prefix) so they
  sort to the top of any directory listing. **Do not** use `00-index.md`
  or other numbered prefixes in hierarchical layouts — the per-section
  filenames are also unnumbered, and the hub's leading underscore is
  the only ordering signal.

## Frontmatter

```yaml
---
tags: ["<keyword-1>", "<keyword-2>", ...]   # 3–7 flat keywords — these become graph nodes
related: ["<other-note>", ...]              # vault-relative paths to other leaf notes
created: YYYY-MM-DD                         # local date the note was written
source: "<url or path>"                     # optional, when the note was distilled from one source
---
```

### Tag rules — the most important part

Tags drive Obsidian's graph view. Two rules:

1. **Flat keywords, no hierarchy.** `["strix", "pentest", "owasp"]` —
   NOT `["topic/strix", "type/note"]`. Hierarchical tags create isolated
   subgraphs and starve the graph of edges.
2. **3–7 tags per note, all shared with at least one other note.** A tag
   that appears on only one note is a dead node. Before tagging, scan
   the existing notes in the target domain and reuse keywords already
   in use.

### `related` rules

- Paths are **vault-relative** without the `.md` extension. Example:
  `"ai-agent-wiki/17-ai-agent-security"` (NOT `[[17-ai-agent-security]]`,
  NOT `wiki/ai-agent-wiki/17-ai-agent-security.md`).
- Include 2–5 related notes — at least one from the same domain, at
  least one cross-domain when one exists.
- Cross-domain references use the same relative-path form:
  `"harness-engineering-wiki/mcp/why-mcp-matters"`.

### `source` rules

- Original URL or path of the source material. Omit when the note is
  written from free text and there is no upstream.
- For clippings, this is the `url:` or `source:` field from the
  clipping's frontmatter, if present.

## Body

```markdown
# <Title>

> <One-line TL;DR — what this page is, in one sentence. Bold the most
> load-bearing 1–3 words.>
> <!-- This blockquote is the only "above-the-fold" copy in Obsidian
> preview; readers decide whether to dive in based on it. -->

## <First Section>

<Content — only non-obvious, hard-to-rediscover insight. No basic
tutorials, no install guides, no "what is X" filler. If a point is in
the official docs of the tool, delete it from this note.>

## <Second Section — optional>

<More insight. Code blocks, tables, and ASCII diagrams are encouraged
when they replace prose.>

## Related

- [[<other-note-1>|<Display Text>]] — <one-line description of the relationship>
- [[<other-note-2>|<Display Text>]] — <one-line description of the relationship>
```

### `## Related` is the graph backbone

Every leaf note MUST end with a `## Related` section whose bullets use
`[[wikilinks]]`. Obsidian's local graph is built from these links. A
note without `## Related` is an isolated node and shows up in the graph
view as a lonely dot.

The `frontmatter:related` list and the `## Related` body section cover
the same edges from two angles: the frontmatter list is for tooling
(graph queries, hub generation), the body section is for readers
(visual graph, navigation). Keep them in sync.

## Worked example

```markdown
---
tags: ["ai-agent", "security-testing", "pentest", "strix", "exploit-validation"]
related: ["ai-agent-wiki/17-ai-agent-security", "ai-agent-wiki/11-mcp", "ai-agent-wiki/00-index"]
created: 2026-09-05
source: "https://www.strix.ai/blog/context-aware-pentesting"
---

# Strix — AI Agent Security Testing

> **Autonomous pentest agents that act like real hackers** — every
> finding is backed by a working PoC exploit, not a static-analysis
> guess.

## Graph of Agents

Strix splits work across specialized agents (recon / exploit /
post-exploit) that share findings in a blackboard. Each agent has the
full toolkit: Caido HTTP proxy, Playwright browser, shell, Python
runtime, Nuclei templates, SAST/DAST.

## PoC-first Validation

A finding only counts if the agent triggered it. This is the direct
answer to scanner false-positive fatigue.

## Related

- [[ai-agent-wiki/17-ai-agent-security|AI Agent 보안 (17)]] — IR playbooks and threat models for agent deployments
- [[ai-agent-wiki/11-mcp|MCP (11)]] — Strix exposes its agents through MCP, the same attack surface it tests
- [[ai-agent-wiki/00-index|AI Agent Wiki Index]] — master catalog of all 19 pages
```

## Anti-patterns

- ❌ Tags as `["topic/strix"]` — hierarchical, no shared graph
- ❌ `## Related` with prose but no `[[wikilinks]]` — graph sees nothing
- ❌ A note with no `## Related` at all — isolated node
- ❌ `related: []` empty list — the frontmatter says "no edges" but
  the body claims edges. Pick one and keep them in sync.
- ❌ `[[17-ai-agent-security]]` — wikilink is in the body, but the
  frontmatter uses a relative path. They should agree on the target.
- ❌ Notes that paraphrase official docs — the point of the wiki is
  unique insight, not a re-statement of what already exists.
