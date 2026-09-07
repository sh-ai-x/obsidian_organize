# obsidian-organize

Claude Code marketplace plugin that organizes an Obsidian vault in the
`hermes-wiki-super` LLM-Wiki style — Karpathy-style leaf notes with flat
keyword tags, `## Related` wikilinks, and dense Obsidian graph edges.

> **Plugin version 0.5.0** — adds hierarchical promotion
> (`add_wiki --hierarchical` / `--major`) for multi-section staged
> research. See [plugins/obsidian-organize/README.md](plugins/obsidian-organize/README.md#hierarchical-mode-multi-section-research).

## What this repo ships

This repository is a Claude Code marketplace (`obsidian-organize-marketplace`)
that bundles the `obsidian-organize` plugin. The plugin exposes five
skills that drive an Obsidian vault through a hermes-wiki-super-shaped
layout. For the full per-skill contract, see
[plugins/obsidian-organize/README.md](plugins/obsidian-organize/README.md).

---

## Installation

### 1. Prerequisites

- [Claude Code](https://docs.claude.com/claude-code) installed and
  authenticated (`claude auth login` if you have not already).
- An Obsidian vault on the local filesystem.
- `gh` CLI authenticated (`gh auth login`) — required for `--mode=super`
  (sub-repo publishes) and for the auto-fix-pr workflow on this repo.

### 2. Add the marketplace

One-time per host. From any directory:

```bash
claude plugin marketplace add sh-ai-x/obsidian_organize
```

Verify it landed:

```bash
claude plugin marketplace list
# → obsidian-organize-marketplace    1.3.0    sh-ai-x
```

### 3. Install the plugin

```bash
claude plugin install obsidian-organize@obsidian-organize-marketplace
```

Verify the install:

```bash
claude plugin list
# → obsidian-organize    0.5.0    obsidian-organize-marketplace
```

### 4. Bootstrap your vault (one-time per vault)

`cd` into the vault root, then:

```bash
/obsidian-organize:bootstrap .
```

This creates the canonical layout under the vault root:
`Clippings/`, `Clippings/processed/`, `wiki/`, `_research/`,
`_archive/research/`, `wiki-map.md`. Safe to re-run — existing files
are preserved.

### 5. Verify the install

From the vault root, run the simplest skill:

```bash
/obsidian-organize:research "JWT security pitfalls"
```

You should see a new file at `_research/jwt-security-pitfalls.md` with
LLM-Wiki-shaped frontmatter. Then promote it:

```bash
/obsidian-organize:add_wiki _research/jwt-security-pitfalls.md
```

The leaf lands at `wiki/<some-domain>/jwt-security-pitfalls.md` with
`## Related` wikilinks to neighboring notes.

### Upgrading

The marketplace tracks the repo's main branch. To pick up new plugin
versions:

```bash
claude plugin update obsidian-organize
```

A major-version bump (e.g. 0.5 → 0.6) may carry migration notes — read
the plugin's release notes / PR diff before upgrading.

### Uninstalling

```bash
claude plugin uninstall obsidian-organize
claude plugin marketplace remove obsidian-organize-marketplace
```

The plugin does not write outside the vault (no `~/.config`, no
`~/.cache`, no global state). Uninstalling leaves the vault's notes
untouched — you can delete the plugin without losing data.

---

## Skills

All five skills live in `plugins/obsidian-organize/skills/`. Each one
has a `SKILL.md` (the spec the agent reads) plus optional `references/`
and `examples/`. The deterministic helpers in `skills/_lib/` implement
the SSOT for argparse, slug derivation, section parsing, and hub
generation.

### `obsidian-organize:bootstrap`

Set up an Obsidian vault with the topic-organizer directory layout
modeled after `hermes-wiki-super`.

```bash
/obsidian-organize:bootstrap <vault-path>
```

**When to use:** first run on a fresh vault, or when migrating an
existing vault to the obsidian-organize layout.

**Creates:**

| Path | Purpose |
|---|---|
| `Clippings/processed/` | Archive of raw clippings after `process_clippings` finishes. |
| `Clippings/.keep` | Marker so the empty directory survives `git`. |
| `wiki/` | Topic-organized wiki notes, one subdirectory per topic. |
| `wiki/<topic>/` | Topic subdirectory; topic note lives at `wiki/<topic>/README.md`. |
| `wiki-map.md` | Master index of all topics. `add_wiki` appends a row per new topic. |
| `_research/` | Staged research files (input to `add_wiki`). |
| `_archive/research/` | Archive for retired research (`remove_wiki`). |

**Status:** still targets the 0.3.x flat layout (`topics/`,
`wiki/<topic>/README.md` per topic). Running `bootstrap` then
`process_clippings` / `add_wiki` on the same vault produces two
incompatible layouts. The fix is a follow-up to update `bootstrap` for
0.4 / 0.5; until then, do not run `bootstrap` on a vault you intend
to use with the 0.4+ skills.

### `obsidian-organize:process_clippings`

Distill raw files dropped into `Clippings/` into Karpathy-style leaf
notes under the right `wiki/<domain>/`. Archive originals.

```bash
/obsidian-organize:process_clippings <clipping-or-folder> \
  [--mode=super|single] [--force] [--dry-run] [--no-backlinks]
```

**When to use:** after a batch of clippings lands in `Clippings/`.
Each clipping becomes one leaf note.

**Two modes:**

- `--mode=super` — each domain lives in its own GitHub repo, mounted
  as a submodule under `wiki/` in `mybotagent/hermes-wiki-super`. Read
  `plugins/obsidian-organize/skills/_shared/hermes-super.md` first.
- `--mode=single` (default) — everything stays in this one repo
  under `wiki/<domain>/`. Same leaf-note shape and distillation
  rules; only the destination and the two-level commit differ.

**Outputs:**

- Leaf note at `wiki/<domain>/.md` with LLM-Wiki
  frontmatter, TL;DR blockquote, and `## Related` wikilinks.
- Row appended to `wiki/<domain>/log.md`.
- Row appended to `wiki-map.md` at the vault root.
- Original clipping moved to `Clippings/processed/`.

### `obsidian-organize:research`

Gather source material on a topic and write a staged research file at
`<vault>/_research/<topic>.md` using the LLM-Wiki frontmatter shape.

```bash
/obsidian-organize:research <topic> [--mode=super|single]
```

**When to use:** when starting a new topic, when extending an
existing one with new sources, or when preparing a 30-min+ research
dossier for later promotion to a leaf note (or to a leaf-note tree,
in 0.5+ with `--hierarchical`).

**Output:** a staged file at `_research/<topic>.md` with:

- `tags:` — flat keyword tags (3–7 keywords)
- `related:` — vault-relative paths to related notes
- `created:` — local date
- `sources:` — original URLs / file paths the note was distilled from
- Body in LLM-Wiki shape (TL;DR blockquote + sections)

`add_wiki` consumes this file directly via `promote()`.

### `obsidian-organize:add_wiki`

Write a new leaf note from a topic, free text, or a staged
`_research/<topic>.md` file. Supports flat and hierarchical layouts.

```bash
/obsidian-organize:add_wiki <topic-or-content> \
  [--mode=super|single] [--force] [--dry-run] [--no-backlinks] \
  [--hierarchical] [--major <name>] [--no-hierarchical]
```

**When to use:** any time you want a new leaf note. The skill reads
the input in this order:

1. `$ARGUMENTS` — topic phrase, free text, or staged-file path.
2. `_research/<topic>.md` if it exists for the topic.
3. Otherwise, ask the user once for a one-line topic.

**Flag reference:**

| Flag | Default | Effect |
|---|---|---|
| `--mode=super` | (single) | Publish to the matching `mybotagent/hermes-wiki-super` sub-repo. |
| `--mode=single` | ✓ | Write into the local vault only. |
| `--force` | off | Overwrite an existing leaf note (default: refuse). |
| `--dry-run` | off | Print the planned write targets and exit without writing. |
| `--no-backlinks` | off | Skip the reverse-pass that touches existing siblings. Does **not** skip the leaf's own `## Related` (always written). |
| `--hierarchical` | off (auto at ≥ 5 numbered sections) | Promote a multi-section staged research into one leaf note per section + auto-generated sub-hub. |
| `--major <name>` | (none) | Adds an extra directory level between `<domain>` and the per-topic directory so sibling research files share a parent theme. |
| `--no-hierarchical` | off | Force flat output even when the staged research has ≥ 5 numbered sections. |

**Hierarchical mode (0.5+):** see [plugins/obsidian-organize/README.md § Hierarchical mode](plugins/obsidian-organize/README.md#hierarchical-mode-multi-section-research)
for the path scheme, worked example, and the Cross-PR contract.

### `obsidian-organize:remove_wiki`

Retire a topic note, archive its staged research, and clean up
back-links.

```bash
/obsidian-organize:remove_wiki <topic> [--dry-run] [--keep-staged]
```

**When to use:** when a topic has decayed or is no longer relevant.

**Behavior:**

- Identifies the topic by its `topic:` frontmatter key.
- Archives the staged research file to `_archive/research/`.
- Removes the topic note.
- Strips the back-link marker from each source file in the vault.

**Status:** targets `topics/<topic>.md` and `[[topics/<topic>]]`
back-link markers (0.3.x). Will be updated to target
`wiki/<domain>/.md` and `[[wiki/<domain>/]]` in a
follow-up.

---

## Vault layout produced

A multi-section staged research file (≥ 5 numbered H2/H3 sections)
becomes a per-section leaf-note tree under the domain, with
auto-generated `_index.md` sub-hubs and (optionally) a
`<major>/_index.md` parent hub. See the plugin README's § Hierarchical
mode for the full path scheme and the worked example.

## Vault conventions inherited from hermes-wiki-super

- `_research/<topic>.md` is the staged input (frontmatter in the
  LLM-Wiki shape) produced by `obsidian-organize:research`.
- `wiki/<domain>/.md` is the leaf note produced by
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

The plugin is **additive** — it does not replace
`hermes-wiki-super/add-wiki` or `hermes-wiki-super/process-clippings`.
It is the formal, version-pinned version of the same convention.

## Cross-PR contract between skill + implementation

The plugin's SKILL.md files are the **spec**; `plugins/obsidian-organize/skills/_lib/`
is the **SSOT** for argument parsing, slug derivation, section
splitting, and index-hub generation. When the two diverge:

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
must merge together or not at all.

## Repository layout

```
obsidian_organize/
├── .claude-plugin/
│   └── marketplace.json          # marketplace manifest — declares the
│                                  # obsidian-organize plugin entry
├── plugins/
│   └── obsidian-organize/       # the actual plugin (versioned independently)
│       ├── .claude-plugin/
│       │   └── plugin.json       # plugin manifest (currently 0.5.0)
│       ├── skills/
│       │   ├── _shared/          # shared references for the LLM-driven flow
│       │   ├── _lib/             # deterministic helpers (0.5 implementation)
│       │   ├── bootstrap/        # vault layout seeder
│       │   ├── process_clippings/
│       │   ├── research/
│       │   ├── add_wiki/         # flat + hierarchical promotion
│       │   └── remove_wiki/
│       ├── tests/                # pytest suite (36 tests)
│       ├── docs/                 # per-plugin migration notes
│       └── README.md             # ← full plugin docs
├── AGENTS.md                    # repo-level agent instructions
├── CLAUDE.md                    # minimal pointer → references/
├── guidelines/                  # coding guidelines
├── hooks/                       # hook matrix
├── iron-laws/                   # iron laws (MUST-8 SSOT)
├── lib/                         # repo-level library code (none currently)
├── scripts/                     # CI scripts (test.sh, validate.py, ...)
├── tools/                       # repo-level tools
├── phases/                      # planning artifacts
├── PRD.md                       # product requirements
├── docs/                        # repo-level docs
├── tests/                       # repo-level tests
└── README.md                    # ← you are here
```

The plugin lives entirely under `plugins/obsidian-organize/`. Everything
outside that directory is repo-level infrastructure for building,
testing, and shipping the marketplace.

## Plugin versioning

The marketplace manifest (`.claude-plugin/marketplace.json`) and the
plugin manifest (`plugins/obsidian-organize/.claude-plugin/plugin.json`)
have independent versions:

- **Marketplace version** (currently `1.3.0`) — bumps when the
  marketplace schema or the plugin list changes.
- **Plugin version** (currently `0.5.0`) — bumps when a skill's
  behavior changes. The plugin's README documents what changed per
  version.

The marketplace version is intentionally ahead of the plugin version
because the marketplace itself has iterated through several plugin
versions.

## Development

```bash
# Run the plugin's test suite locally
bash scripts/test.sh

# Run the repo-level validate
python3 scripts/validate.py

# Check the CLAUDE.md / iron-laws / hooks / guidelines pointers
cat CLAUDE.md
```

Repo-level meta documents (read these when starting work):

- [CLAUDE.md](CLAUDE.md) — minimal pointer to the linked index files.
- [AGENTS.md](AGENTS.md) — same, for code-generation agents.
- [iron-laws/index.md](iron-laws/index.md) — MUST-8 iron laws (SSOT).
- [guidelines/index.md](guidelines/index.md) — coding style (Karpathy-style, abbreviated).
- [hooks/index.md](hooks/index.md) — hook matrix (MUST-13 SSOT).
- [docs/CODEBASE-MAP.md](docs/CODEBASE-MAP.md) — regenerate via
  `/dev-kit:bootstrap --full-claude-md`.

## License

MIT — see plugin manifest for author / license metadata.
