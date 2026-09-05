# obsidian-organize

A Claude Code plugin that organizes an Obsidian vault by topic.

## Skills

| Skill ID | Purpose |
|---|---|
| `obsidian-organize:research` | Gather source material on a topic into a staged research file. |
| `obsidian-organize:add_wiki` | Promote a staged research file into a topic note. |
| `obsidian-organize:remove_wiki` | Retire a topic note, archive the staged research, and clean up back-links. |

## Layout

```
plugins/obsidian-organize/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── research/
│   │   ├── SKILL.md
│   │   └── references/output-schema.md
│   ├── add_wiki/
│   │   ├── SKILL.md
│   │   └── references/frontmatter.md
│   └── remove_wiki/
│       ├── SKILL.md
│       └── references/cleanup-rules.md
├── tests/
│   ├── fixtures/vault/
│   ├── test_research.py
│   ├── test_add_wiki.py
│   ├── test_remove_wiki.py
│   └── test_integration.py
└── README.md
```

## Vault conventions inherited from hermes-wiki-super

This plugin is additive — it does **not** replace `hermes-wiki-super/add-wiki` or
`hermes-wiki-super/process-clippings`. It sits one layer above them:

- `_research/<topic>.md` is produced by `process-clippings` (existing) or by
  `obsidian-organize:research` (this plugin) and is the staged input.
- `topics/<topic>.md` is produced by `add-wiki` (existing) or by
  `obsidian-organize:add_wiki` (this plugin).
- `obsidian-organize:remove_wiki` retires a topic, archives its staged research
  to `_archive/research/<topic>-<timestamp>.md`, and drops `[[wikilink]]`
  back-references from source files.

## Acceptance criteria

See `phases/obsidian-topic-organizer/step{0..4}.md` for per-step AC.
