"""Tests for `obsidian-organize:remove_wiki`."""

from __future__ import annotations

import logging

from _lib import (
    parse_frontmatter,
    promote,
    resolve_staged_path,
    resolve_topic_path,
    retire,
    write_staged_file,
    ResearchInput,
)


def _promote(vault_root, fixed_now, topic="hermes-protocol"):
    write_staged_file(
        vault_root,
        ResearchInput(
            topic=topic,
            sources=["sources/source-a.md", "sources/source-b.md"],
        ),
        now=fixed_now,
    )
    return promote(vault_root, topic, now=fixed_now)


def test_remove_wiki_dry_run_does_not_mutate(vault_root, fixed_now):
    _promote(vault_root, fixed_now)
    result = retire(vault_root, "hermes-protocol", dry_run=True, now=fixed_now)

    assert result.dry_run is True
    assert result.topic_note_deleted is True
    assert resolve_topic_path(vault_root, "hermes-protocol").exists()
    assert resolve_staged_path(vault_root, "hermes-protocol").exists()


def test_remove_wiki_archives_staged_and_deletes_topic(vault_root, fixed_now):
    _promote(vault_root, fixed_now)
    result = retire(vault_root, "hermes-protocol", now=fixed_now)

    assert result.dry_run is False
    assert result.topic_note_deleted is True
    assert not resolve_topic_path(vault_root, "hermes-protocol").exists()
    assert not resolve_staged_path(vault_root, "hermes-protocol").exists()
    assert result.archived_to is not None
    assert result.archived_to.exists()
    assert result.archived_to.read_text(encoding="utf-8").startswith("---\n")

    # Archived file's status must be 'archived'.
    fm, _ = parse_frontmatter(result.archived_to.read_text(encoding="utf-8"))
    assert fm["status"] == "archived"


def test_remove_wiki_strips_backlinks_from_source_files(vault_root, fixed_now):
    _promote(vault_root, fixed_now)
    retire(vault_root, "hermes-protocol", now=fixed_now)

    for src in ("sources/source-a.md", "sources/source-b.md"):
        text = (vault_root / src).read_text(encoding="utf-8")
        assert "[[topics/hermes-protocol]]" not in text, f"back-link leaked in {src}"


def test_remove_wiki_keep_staged_marks_archived_in_place(vault_root, fixed_now):
    _promote(vault_root, fixed_now)
    result = retire(
        vault_root, "hermes-protocol", keep_staged=True, now=fixed_now
    )

    assert result.archived_to == resolve_staged_path(vault_root, "hermes-protocol")
    assert result.archived_to.exists()
    fm, _ = parse_frontmatter(result.archived_to.read_text(encoding="utf-8"))
    assert fm["status"] == "archived"


def test_remove_wiki_fails_without_topic_note(vault_root, fixed_now):
    try:
        retire(vault_root, "ghost-topic", now=fixed_now)
    except FileNotFoundError:
        return
    raise AssertionError("expected FileNotFoundError on missing topic note")


# --------------------------------------------------------------------------- #
# F4 — scan_backlinks silently dropping non-UTF-8 files (PR #5 review)
# --------------------------------------------------------------------------- #


def test_scan_backlinks_warns_on_non_utf8_file(tmp_path, caplog):
    """F4: a non-UTF-8 .md file must NOT be silently dropped from the
    backlink scan.

    Previously `scan_backlinks` did `except UnicodeDecodeError: continue`
    — making an undecodable .md file invisible. The downstream
    consequence: `remove_wiki.retire` would delete the topic note but
    leave back-link markers in that file forever, with no signal to
    anyone.

    The fix surfaces the failure via `logger.warning` naming the file,
    and the scan still completes for every other file. This test
    verifies both behaviors.
    """
    from _lib.paths import scan_backlinks

    # A valid .md file with a back-link marker.
    valid = tmp_path / "valid.md"
    valid.write_text(
        "<!-- back-linked from [[topics/foo]] on 2026-09-05T12:00:00Z -->\n",
        encoding="utf-8",
    )

    # A genuinely undecodable .md file — raw bytes that are NOT valid UTF-8.
    # 0xff, 0xfe, 0x00 are invalid UTF-8 start bytes / surrogate halves.
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe\x00bad")

    with caplog.at_level(logging.WARNING, logger="_lib.paths"):
        hits = scan_backlinks(tmp_path, "foo")

    # The valid file's back-link IS found — the scan did not abort on
    # the bad file.
    assert any(h.file == valid for h in hits), (
        f"scan aborted on the non-UTF-8 file; hits={[h.file for h in hits]}"
    )

    # A warning naming the bad file was emitted (not silently dropped).
    bad_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "bad.md" in r.getMessage()
    ]
    assert bad_warnings, (
        f"expected a warning mentioning bad.md, got: "
        f"{[(r.levelname, r.getMessage()) for r in caplog.records]}"
    )
