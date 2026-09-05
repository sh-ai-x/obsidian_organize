# remove_wiki — cleanup rules

The removal pass is destructive: it deletes the topic note, moves the staged
file, and edits every source file. This document pins the rules so the
behavior is deterministic and reviewable.

## Scan-root

- Default: `<vault>/`.
- Excluded subtrees: `topics/`, `_research/`, `_archive/`, `.obsidian/`,
  `.git/`, `node_modules/`, `.trash/`.

## Back-link marker

The line added by `add_wiki` looks like:

```
<!-- back-linked from [[topics/<topic>]] on <ISO-8601> -->
```

`remove_wiki` removes the entire line containing this marker. If the marker
appears multiple times in the same file (a source used by multiple topics),
only the matching line is removed.

## Archive path

```
<vault>/_archive/research/<topic>-<ISO-8601>.md
```

- `<ISO-8601>` is the time at which `remove_wiki` ran, in seconds.
- Colons (`:`) in the timestamp are replaced with dashes (`-`) to avoid
  filesystem issues on macOS / Windows.
- Example: `_archive/research/hermes-protocol-2026-09-05T11-00-00Z.md`.

## Topic-note deletion

After staging the archive and source edits, the topic note at
`<vault>/topics/<topic>.md` is deleted. There is **no soft-delete tombstone
inside the vault** — the archive path is the only artifact that survives.

## Dry-run

`--dry-run` performs all reads and planning, then prints:

```
[plan] archive:  <vault>/_research/<topic>.md → <archive-path>
[plan] edit:     <vault>/sources/a.md  (1 line removed)
[plan] edit:     <vault>/sources/b.md  (1 line removed)
[plan] delete:   <vault>/topics/<topic>.md
[plan] total:    2 source edits, 1 topic-note deletion, 1 archive move
```

…and exits 0 with **no writes**.

## Algorithm (pseudocode)

```python
def remove_wiki(vault_root: Path, topic: str, dry_run: bool) -> Report:
    topic_note = vault_root / "topics" / f"{topic}.md"
    staged = vault_root / "_research" / f"{topic}.md"
    archive = vault_root / "_archive" / "research" / f"{topic}-{now_compact()}.md"

    assert topic_note.exists(), "no active topic at {topic_note}"
    sources_to_edit = scan_for_backlinks(vault_root, topic)

    if dry_run:
        return Report(plan=[archive_move, *source_edits, topic_deletion])

    if staged.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        staged.rename(archive)
        update_frontmatter(archive, status="archived")

    for src, line_no in sources_to_edit:
        remove_line(src, line_no)

    topic_note.unlink()
    return Report(done=[archive_move, *source_edits, topic_deletion])
```
