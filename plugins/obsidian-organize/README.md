# obsidian-organize

Topic-organizer for Obsidian vaults. Sets up the `Clippings-processed / wiki / wiki-map` layout that `hermes-wiki-super` already uses, then drives four skills that take a topic from "raw clippings" through "research file" to "canonical topic note" and back.

This plugin is **additive** — it sits one layer above `hermes-wiki-super/add-wiki` and `hermes-wiki-super/process-clippings`. It does not shadow or replace them.

## Install

The plugin is published through the **obsidian-organize-marketplace** marketplace (the `.claude-plugin/marketplace.json` in this repository).

```bash
# Add the marketplace
claude plugin marketplace add sh-ai-x/obsidian_organize

# Install the plugin (use plugin@marketplace form to disambiguate)
claude plugin install obsidian-organize@obsidian-organize-marketplace
```

Or via the slash command:

```
/plugin marketplace add sh-ai-x/obsidian_organize
/plugin install obsidian-organize@obsidian-organize-marketplace
```

Once installed, the four skills are available as namespace-prefixed slash commands (see [Invocation](#invocation) below).

## Skills

| Skill | Purpose |
|---|---|
| `obsidian-organize:bootstrap` | Create the canonical vault layout (`Clippings/processed/`, `wiki/`, `wiki-map.md`, `_research/`, `_archive/research/`). Idempotent; refuses to clobber without `--force`. |
| `obsidian-organize:research` | Gather source material on a topic and write a staged research file at `<vault>/_research/<topic>.md`. |
| `obsidian-organize:add_wiki` | Promote a staged research file into a canonical topic note at `wiki/<topic>/README.md`, append a row to `wiki-map.md`, and back-link each source. |
| `obsidian-organize:remove_wiki` | Retire a topic note: move the staged file to `_archive/research/`, drop the `wiki-map.md` row, and strip the back-link marker from each source. |

### Invocation

```
/obsidian-organize:bootstrap  <vault-path>                  [--force] [--topics "a,b,c"]
/obsidian-organize:research   <topic>                       [--source URL] [--from <path>] [--append]
/obsidian-organize:add_wiki   <topic-or-file>               [--force] [--no-backlinks]
/obsidian-organize:remove_wiki <topic>                      [--dry-run] [--keep-staged]
```

All four skills read the vault root from `OBSIDIAN_VAULT` (env) or the `--vault <path>` flag and fail with a clear message if neither is set.

## Layout

```
plugins/obsidian-organize/
├── .claude-plugin/
│   └── plugin.json                          # plugin manifest (name, version, skills[])
├── skills/
│   ├── bootstrap/
│   │   ├── SKILL.md
│   │   └── references/layout.md             # pinned directory tree + per-path contracts
│   ├── research/
│   │   ├── SKILL.md
│   │   └── references/output-schema.md      # canonical frontmatter + body for staged files
│   ├── add_wiki/
│   │   ├── SKILL.md
│   │   └── references/frontmatter.md        # canonical topic-note frontmatter
│   ├── remove_wiki/
│   │   ├── SKILL.md
│   │   └── references/cleanup-rules.md      # scan-root, archive naming, back-link removal
│   └── _lib/                                # shared Python helpers (paths/frontmatter/slug)
│       ├── __init__.py
│       ├── paths.py
│       ├── frontmatter.py
│       ├── slug.py
│       ├── bootstrap.py
│       ├── research.py
│       ├── add_wiki.py
│       └── remove_wiki.py
├── tests/
│   ├── conftest.py
│   ├── fixtures/vault/sources/              # source-a.md, source-b.md
│   ├── test_bootstrap.py
│   ├── test_research.py
│   ├── test_add_wiki.py
│   ├── test_remove_wiki.py
│   └── test_integration.py
└── README.md
```

## Vault conventions inherited from hermes-wiki-super

The layout mirrors `hermes-wiki-super`'s directory structure so the same upstream skills (`process-clippings`, `add-wiki`) work unmodified on vaults bootstrapped by this plugin.

| Path | Owner skill |
|---|---|
| `Clippings/processed/` | `hermes-wiki-super/process-clippings` (untouched by this plugin) |
| `wiki/<topic>/README.md` | `obsidian-organize:add_wiki` |
| `wiki-map.md` | `obsidian-organize:bootstrap` (template) → `add_wiki` (append row) → `remove_wiki` (drop row) |
| `_research/<topic>.md` | `obsidian-organize:research` (write) → `remove_wiki` (move to `_archive/research/`) |
| `_archive/research/<topic>-<ISO-8601>.md` | `obsidian-organize:remove_wiki` |

See `skills/bootstrap/references/layout.md` for the pinned directory tree and per-path contracts.

## Frontmatter quick reference

`_research/<topic>.md` (staged, produced by `research`):

```yaml
---
topic: <topic>
created: <ISO-8601>
sources:
  - <url or path>
status: staged            # → promoted (by add_wiki) → archived (by remove_wiki)
---
```

`wiki/<topic>/README.md` (topic note, produced by `add_wiki`):

```yaml
---
topic: <topic>
created: <ISO-8601>
updated: <ISO-8601>
tags: [topic/<topic>]
sources:
  - <url-or-path>
status: active            # → retired (by remove_wiki), with retired_at / retired_to keys
---
```

Source files get a back-link marker appended on promotion and stripped on removal:

```
<!-- back-linked from [[wiki/<topic>/README]] on <ISO-8601> -->
```

## Tests

```bash
cd plugins/obsidian-organize
pytest -q
```

The test suite uses an isolated fixture vault under `tests/fixtures/vault/` and covers each skill in isolation (`test_<skill>.py`) plus a full bootstrap → research → add_wiki → remove_wiki round-trip (`test_integration.py`).

## Marketplace registration

This plugin is registered in the `obsidian-organize-marketplace` (v1.1.0) at `<repo-root>/.claude-plugin/marketplace.json`:

```json
{
  "name": "obsidian-organize-marketplace",
  "owner": { "name": "sh-ai-x" },
  "plugins": [
    {
      "name": "obsidian-organize",
      "version": "0.2.0",
      "source": "./plugins/obsidian-organize",
      "category": "productivity"
    }
  ]
}
```

Validate the registration locally:

```bash
claude plugin validate plugins/obsidian-organize      # ✔ plugin.json + every SKILL.md
claude plugin validate .claude-plugin/marketplace.json # ✔ marketplace.json ↔ plugin.json
```

`bin/validate-marketplace.sh` is a non-CLI equivalent that fails fast if the marketplace JSON drifts from the plugin manifest.

## Acceptance criteria

Per-step AC for the `obsidian-organize` plan lives in `phases/obsidian-topic-organizer/step{0..4}.md` at the repo root.

## License

MIT.