# obsidian-organize

A plugin for **Claude Code**, **Codex**, and **Google Antigravity (`agy`)** that organizes an Obsidian vault in the
`hermes-wiki-super` LLM-Wiki style.

> **Version 0.5.0** — adds hierarchical promotion (`add_wiki
> --hierarchical` / `--major`) for multi-section staged research.
> See § Hierarchical mode below.

## Skills

| Skill ID | Purpose |
|---|---|
| `obsidian-organize:bootstrap` | Create the canonical vault layout (Clippings/, wiki/, _research/, _archive/, wiki-map.md). |
| `obsidian-organize:process_clippings` | Distill raw Clippings/ files into Karpathy-style leaf notes under the right `wiki/<domain>/`. Archive originals. |
| `obsidian-organize:research` | Stage source material on a topic into `_research/<topic>.md` using the LLM-Wiki frontmatter shape. |
| `obsidian-organize:add_wiki` | Write a new leaf note from a topic, free text, or staged file. Supports flat and hierarchical layouts. |
| `obsidian-organize:remove_wiki` | Retire a leaf note and clean up the back-links. |

## Invocation

```
/obsidian-organize:add_wiki <topic-or-content> [--mode=super|single] [--force] [--dry-run] [--no-backlinks] [--hierarchical] [--major <name>] [--no-hierarchical]
```

- `<topic-or-content>` is either a topic phrase ("JWT security pitfalls")
  or raw content to be distilled into a leaf note.
- `--hierarchical` — promote a multi-section staged research into a
  per-section leaf-note tree. Auto-enabled when the staged research
  has **≥ 5 numbered sections** (H2 `## §N …` or H3 `### N. …`),
  unless `--no-hierarchical` is also passed. See § Hierarchical mode.
- `--major <name>` — only meaningful with `--hierarchical`. Adds an
  extra directory level between `<domain>` and the per-topic directory
  so sibling research files can share a parent theme.
- `--no-hierarchical` — force the flat single-file output even when
  the staged research has ≥ 5 sections.

See `skills/add_wiki/SKILL.md` for the full contract (auto-enable
threshold, path scheme, back-link rules, troubleshooting).

## Layout

```
plugins/obsidian-organize/
├── plugin.json              # Antigravity (agy) manifest
├── .claude-plugin/
│   └── plugin.json          # Claude Code manifest (version 0.5.0)
├── .codex-plugin/
│   └── plugin.json          # Codex manifest
├── skills/
│   ├── _shared/             # shared references for the LLM-driven flow
│   │   ├── note-schema.md   # canonical leaf-note frontmatter + body
│   │   └── wiki-router.md   # which wiki/<domain>/ a topic belongs in
│   ├── _lib/                # DETERMINISTIC HELPERS — argparse, slug,
│   │   │                      # section parsing, hub generation. SSOT
│   │   │                      # for the cross-PR contract (see below).
│   │   ├── __init__.py
│   │   ├── add_wiki.py      # promote() — flat + hierarchical modes
│   │   ├── paths.py         # resolve_hierarchical_paths() etc.
│   │   ├── research.py      # write_hierarchical_staged_file() etc.
│   │   ├── slug.py          # section_title_to_slug() etc.
│   │   ├── frontmatter.py   # parse / serialize LLM-Wiki frontmatter
│   │   ├── bootstrap.py     # 0.3.x vault bootstrap (legacy)
│   │   └── remove_wiki.py   # 0.3.x leaf retire (legacy)
│   ├── bootstrap/           # NOT YET MIGRATED — still seeds 0.3.x layout
│   │   ├── SKILL.md
│   │   └── references/layout.md
│   ├── process_clippings/   # 0.4 (LLM-driven, hermes-style)
│   │   └── SKILL.md
│   ├── research/            # 0.4 (hermes-style frontmatter)
│   │   ├── SKILL.md
│   │   └── references/output-schema.md
│   ├── add_wiki/            # 0.5 (LLM-driven + flat / hierarchical modes)
│   │   └── SKILL.md
│   └── remove_wiki/         # NOT YET MIGRATED — targets 0.3.x topics/
│       ├── SKILL.md
│       └── references/cleanup-rules.md
├── tests/
│   ├── test_hierarchical_promotion.py   # NEW in 0.5: 15 tests
│   ├── test_add_wiki.py
│   ├── test_bootstrap.py
│   ├── test_integration.py
│   ├── test_remove_wiki.py
│   └── test_research.py
├── docs/
│   └── migration-0.3-to-0.4.md
└── README.md
```

## Vault conventions inherited from hermes-wiki-super

The 0.4 / 0.5 redesign mirrors `hermes-wiki-super` directly. Leaf
notes land under `wiki/<domain>/` (one folder per knowledge area),
each with flat keyword tags, an explicit `related:` list, a TL;DR
blockquote, and a `## Related` section whose `[[wikilinks]]` drive
Obsidian's graph view. See `skills/_shared/note-schema.md` for the
full shape and `skills/_shared/wiki-router.md` for routing rules.

The plugin is **additive** — it does not replace
`hermes-wiki-super/add-wiki` or `hermes-wiki-super/process-clippings`.
It is the formal, version-pinned version of the same convention.

- `_research/<topic>.md` is the staged input (frontmatter in the
  LLM-Wiki shape) produced by `obsidian-organize:research`.
- `wiki/<domain>/<filename>.md` is the leaf note produced by
  `obsidian-organize:process_clippings` (input: a Clippings/ file) or
  `obsidian-organize:add_wiki` (input: a topic, free text, or staged
  file).
- `wiki-map.md` at the vault root is the master index, with bullets
  grouped by domain.
- `wiki/<domain>/log.md` is the per-domain change log, appended on
  every ingest.
- `Clippings/processed/` is the archive of originals after
  `process_clippings` finishes.
- `obsidian-organize:remove_wiki` retires a leaf note and cleans up
  the `## Related` back-links in sibling notes.

## Hierarchical mode (multi-section research)

When a staged research file has many sections — `## §1`, `## §2`, …,
or `### 1.`, `### 2.`, … — a single flat topic note becomes a
1,000-line monster that defeats Obsidian navigation. The `--hierarchical`
flag (auto-enabled at **≥ 5 numbered sections**) splits the staged
research into one leaf note per section plus an auto-generated
`_index.md` sub-hub. With `--major <name>`, an extra directory level
is added so sibling research files can share a parent theme.

### Path scheme

| Invocation | Per-section leaf path | Auto-generated hubs |
|---|---|---|
| `--hierarchical` (no `--major`) | `wiki/<domain>/<slug>/<section>.md` | `wiki/<domain>/<slug>/_index.md` (sub-hub) |
| `--hierarchical --major <m>` | `wiki/<domain>/<m>/<slug>/<section>.md` | `wiki/<domain>/<m>/<slug>/_index.md` (sub-hub) + `wiki/<domain>/<m>/_index.md` (major hub) |
| No flag, single-section research | `wiki/<domain>/<slug>.md` | (none) |

`<slug>` is the research filename without the `.md` extension.
`<section>` is a kebab-case derivative of the section heading (e.g.
`## §3 Prompt Injection` → `prompt-injection.md`).

### When to use

Use hierarchical mode when:

- The staged research has ≥ 5 sections **and** each section is
  self-contained enough to stand alone as a leaf note (the typical
  case for 30-min+ research dossiers).
- Multiple sibling research files share a parent theme (e.g.
  `core-ai-security-threats`, `core-ai-security-defenses`,
  `core-ai-security-frameworks`). Group them under `--major
  core-ai-security` so the wiki gains a natural 3-level hierarchy.

Do **not** use hierarchical mode for free-text input with no staged
research, single-section staged research, or when the user asked for a
single named topic.

### Worked example

Three staged research files: `core-ai-security-threats.md`
(14 sections), `core-ai-security-defenses.md` (10 sections),
`core-ai-security-frameworks.md` (10 sections). Invocation:

```
/obsidian-organize:add_wiki core-ai-security-threats \
  --hierarchical --major core-ai-security
/obsidian-organize:add_wiki core-ai-security-defenses \
  --hierarchical --major core-ai-security
/obsidian-organize:add_wiki core-ai-security-frameworks \
  --hierarchical --major core-ai-security
```

Produced tree (38 files total):

```
wiki/ai-agent-wiki/core-ai-security/
├── _index.md                                     (major hub — links the 3 sub-hubs)
├── threats/
│   ├── _index.md                                 (sub-hub)
│   ├── 01-executive-summary.md
│   ├── 02-owasp-llm-top-10.md
│   ├── ...                                       (12 more leaves)
├── defenses/
│   ├── _index.md
│   ├── 01-executive-summary.md
│   ├── ...                                       (9 more leaves)
└── frameworks/
    ├── _index.md
    ├── 01-executive-summary.md
    └── ...                                       (9 more leaves)
```

Every per-section leaf links:

- `[[<slug>/_index.md|<Slug> sub-hub]]`
- `[[<major>/_index.md|<Major> hub]]` (when `--major` is set)
- Each sister `<other-slug>/_index.md` sub-hub (when `--major` is set)
- `[[<domain>/00-index.md|<Domain> index]]`

No leaf is more than two hops from the domain index. The Obsidian
graph view shows a dense mesh: per-section leaves → sub-hub →
major hub → 00-index.

### Cross-PR contract

The plugin's SKILL.md files are the **spec**; `skills/_lib/` is the
**SSOT** for argument parsing, slug derivation, section splitting,
and index-hub generation. When the two diverge:

- If the SKILL.md describes a flag the implementation does not yet
  honor → treat the SKILL.md as the spec; flag the gap; refuse to
  merge until implementation catches up.
- If the implementation supports a flag the SKILL.md does not
  describe → flag the gap; the SKILL.md MUST be updated before
  merging any implementation change.
- Flag interactions live in the SKILL.md (`--hierarchical` +
  `--major`; `--hierarchical` auto-enable at ≥ 5 sections). The
  implementation MUST follow the auto-enable rule exactly — flipping
  the threshold is a behavior change, not a bug fix.

PRs that touch the spec (SKILL.md) and the implementation (`_lib/`)
must merge together or not at all — a partial merge leaves the
plugin describing features that do not exist (or vice versa) and
breaks `obsidian-organize:bootstrap` consumers.

### Troubleshooting

- **`--hierarchical` ignored on a clearly multi-section input.** The
  auto-enable rule requires **≥ 5 numbered sections** AND the
  section pattern to be `## §N …` or `### N. …`. Recovery: re-number
  the headings to match the pattern, or pass `--hierarchical`
  explicitly to force-enable.
- **Sibling research files land in separate top-level dirs.** The
  `--major` flag was not passed on the second/third invocations.
  Recovery: re-run with the same `--major <name>` on every sibling.
- **`--no-backlinks` did not skip Related on the new leaf.** The
  implementation always writes the leaf's `## Related`;
  `--no-backlinks` only skips the *reverse* pass that touches
  existing siblings. By design — a leaf with no `## Related` is
  an isolated node.
- **`gh` auth failure in `--mode=super`.** Stop, surface the gh
  unauthenticated state, do not silently fall back to
  `--mode=single`.
- **Auto-enable kicked in for a 3-section research.** Bug — the
  threshold is 5, not 3. File an issue with the section count and
  output path.
- **Vault root cannot be inferred.** `obsidian-organize:bootstrap`
  MUST be run before `add_wiki`; without it the vault root is unknown
  and the skill refuses.

## 0.3 → 0.4 / 0.5 migration

0.3.x produced `topics/<topic>.md` notes with hierarchical
`topic/<topic>` tags and no Obsidian graph edges. 0.4 produces
`wiki/<domain>/<filename>.md` notes with flat keyword tags and a
`## Related` section that lights up the graph. 0.5 adds hierarchical
promotion for multi-section staged research. Existing 0.3.x notes
need a one-time migration before the new layout will render
correctly in Obsidian — see
[`docs/migration-0.3-to-0.4.md`](docs/migration-0.3-to-0.4.md) for
the per-note steps.

### Status of the legacy 0.3.x code paths

- **`skills/_lib/bootstrap.py` + `remove_wiki.py`** — 0.3.x
  deterministic helpers, kept for the legacy pytest suite. No new
  functionality. Removal is a follow-up that runs the red-first
  removal cycle. The 0.5 deterministic helpers (`add_wiki.py`,
  `paths.py`, `research.py`, `slug.py`) are NOT legacy — they
  implement the current spec.
- **`skills/bootstrap/SKILL.md` and `references/layout.md`** — still
  describe the 0.3.x flat layout (`topics/`, `wiki/<topic>/README.md`
  per topic, `## Topics` rows in `wiki-map.md`). Running
  `bootstrap` then `process_clippings` / `add_wiki` on the same vault
  produces two incompatible layouts. The fix is to update
  `bootstrap` for 0.4 in a follow-up PR; until then, do not run
  `bootstrap` on a vault you intend to use with 0.4 / 0.5.
- **`skills/remove_wiki/SKILL.md`** — targets `topics/<topic>.md`
  and `[[topics/<topic>]]` back-link markers. Will be updated to
  target `wiki/<domain>/<filename>.md` and `[[wiki/<domain>/<filename>]]`
  in the same follow-up.

The four 0.4 / 0.5 skills (`process_clippings`, `research`,
`add_wiki` — flat + hierarchical, and the new
`add_wiki --hierarchical --major` paths) plus the shared references
(`_shared/note-schema.md`, `_shared/wiki-router.md`) are the only
paths that emit the new layout. The other three are still 0.3.x.

## Acceptance criteria

See `phases/obsidian-topic-organizer/step{0..4}.md` for per-step AC.

For 0.5 specifically:

- [x] `add_wiki --hierarchical` splits a ≥ 5-section staged research
      into per-section leaves under `wiki/<domain>/<slug>/`.
- [x] `add_wiki --hierarchical --major <m>` adds the major-hub
      layer and links sibling sub-hubs.
- [x] `--no-hierarchical` forces flat output even at the
      auto-enable threshold.
- [x] Per-section slug disambiguation when two section titles reduce
      to the same fallback slug (covered by
      `test_section_title_to_slug_fallback_disambiguates_with_sec_num`).
- [x] No-leaf-leaf or sub-hub collision (covered by the 15 tests
      in `tests/test_hierarchical_promotion.py`).
