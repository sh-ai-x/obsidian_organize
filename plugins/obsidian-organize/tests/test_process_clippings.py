"""Tests for `obsidian-organize:process_clippings`.

process_clippings scans `<vault>/Clippings/` (excluding `processed/`) and
for every `.md` file:

  1. Derives a topic slug from the first H1 in the body (fallback: filename).
  2. Creates `wiki/<topic>/README.md` (LLM-Wiki style) if missing.
  3. Creates `wiki/<topic>/clippings/<safe-name>.md` with a frontmatter
     envelope + the original body verbatim.
  4. Moves the source file to `Clippings/processed/<safe-name>.md`.
  5. Appends a row to `wiki-map.md` (creates the file with the template
     if missing).

Run with: `pytest -q tests/test_process_clippings.py`
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from _lib import (
    ClippingPage,
    ProcessClippingsResult,
    extract_topic_slug,
    process_clippings,
    render_clipping_page,
    render_topic_readme,
    resolve_clipping_page,
    resolve_processed_path,
    resolve_topic_dir,
    unique_processed_path,
)


# ---------- pure-function tests (no vault) ---------------------------------


def test_extract_topic_slug_from_h1() -> None:
    text = "# AI Security Career Roadmap\n\nBody…"
    assert extract_topic_slug(text, "2026년_09월_05일_AI_보안_취업_로드맵.md") == "ai-security-career-roadmap"


def test_extract_topic_slug_strips_utf8_bom() -> None:
    """MINOR 7: a leading UTF-8 BOM must not push the H1 past the
    scan — otherwise the first line is "﻿# Heading" which doesn't
    match the H1 prefix and the function silently falls back to the
    filename (a misleading topic slug).
    """
    text_bom = "﻿# AI Security Career Roadmap\n\nBody…"
    assert (
        extract_topic_slug(text_bom, "ignored_filename.md")
        == "ai-security-career-roadmap"
    )


def test_extract_topic_slug_from_filename_when_no_h1() -> None:
    text = "no heading here, just prose"
    assert extract_topic_slug(text, "LangChain_Research_2026-09-05.md") == "langchain-research-2026-09-05"


def test_extract_topic_slug_handles_non_ascii() -> None:
    """The H1 is non-ASCII-only so `normalize_topic_slug` strips it to "".
    Falls back to the filename stem; the stem is also non-ASCII-only so
    `normalize_topic_slug` returns "" again; the function then takes
    `_sanitize_last_resort_slug` — which preserves non-ASCII letters
    while still replacing `_` with `-` (a markdown-hostile char in
    some contexts) and stripping `/`, `\\`, etc. The expected value
    is therefore `"한국-보안-리서치"` — every `_` in the original stem
    collapsed to `-`, and the resulting string survives as a path
    segment because modern filesystems handle Unicode in directory
    names.
    """
    text = "# 한경 보안 리서치\n\n"
    slug = extract_topic_slug(text, "한국_보안_리서치.md")
    assert slug == "한국-보안-리서치"


def test_render_topic_readme_template() -> None:
    out = render_topic_readme(topic="ai-security", created_iso="2026-09-05T12:00:00Z")
    assert "# ai-security" in out
    assert "Karpathy-style LLM Wiki" in out
    assert "Created: 2026-09-05T12:00:00Z" in out
    # Auto-marker block for `add_wiki`-style appenders.
    assert "<!-- obsidian-organize:topic:auto-start -->" in out
    assert "<!-- obsidian-organize:topic:auto-end -->" in out


def test_render_clipping_page_envelope() -> None:
    page = render_clipping_page(
        source_filename="2026년_09월_05일_AI_보안_리서치.md",
        topic="ai-security",
        body="# AI 보안 리서치\n\n본문…",
        processed_iso="2026-09-05T12:00:00Z",
    )
    assert page.startswith("---\n")
    assert "type: clipping" in page
    assert "topic: ai-security" in page
    assert "source: 2026년_09월_05일_AI_보안_리서치.md" in page
    # `processed_iso` contains `:` so the serializer quotes it — that's valid YAML.
    assert "processed:" in page and "2026-09-05T12:00:00Z" in page
    assert "# AI 보안 리서치" in page


def test_resolve_topic_dir() -> None:
    assert resolve_topic_dir(Path("/vault"), "ai-security") == Path("/vault/wiki/ai-security")


def test_resolve_clipping_page() -> None:
    p = resolve_clipping_page(Path("/vault"), "ai-security", "My Clipping.md")
    assert p == Path("/vault/wiki/ai-security/clippings/My Clipping.md")


def test_unique_processed_path_no_collision(tmp_path: Path) -> None:
    # Nothing exists yet — desired target returned as-is.
    p = unique_processed_path(tmp_path, "a.md")
    assert p == tmp_path / "a.md"


def test_unique_processed_path_with_collision(tmp_path: Path) -> None:
    # The desired target already exists → must be disambiguated.
    (tmp_path / "a.md").touch()
    p = unique_processed_path(tmp_path, "a.md")
    assert p != tmp_path / "a.md"
    assert p.name.startswith("a-")
    assert p.suffix == ".md"


# ---------- end-to-end tests against a real vault ---------------------------


def _write_clipping(vault: Path, name: str, body: str) -> Path:
    d = vault / "Clippings"
    d.mkdir(exist_ok=True)
    p = d / name
    p.write_text(body, encoding="utf-8")
    return p


def test_process_clippings_empty_clippings_is_noop(vault_root: Path, fixed_now) -> None:
    (vault_root / "Clippings").mkdir(exist_ok=True)
    result = process_clippings(vault_root, now=fixed_now, dry_run=False)
    assert result.processed == []
    assert result.skipped == []
    assert result.failed == []
    assert not (vault_root / "wiki").exists()


def test_process_clippings_single_clipping_creates_wiki_entry(
    vault_root: Path, fixed_now
) -> None:
    src = _write_clipping(
        vault_root,
        "2026-09-05-AI-Security-Research.md",
        "# AI Security Research\n\nBody line 1.\nBody line 2.\n",
    )
    result = process_clippings(vault_root, now=fixed_now, dry_run=False)

    # Returns metadata
    assert len(result.processed) == 1
    assert result.processed[0].topic == "ai-security-research"
    assert result.processed[0].source == src

    # wiki/<topic>/README.md exists
    readme = vault_root / "wiki" / "ai-security-research" / "README.md"
    assert readme.exists()
    assert "# ai-security-research" in readme.read_text(encoding="utf-8")

    # wiki/<topic>/clippings/<safe>.md exists with body preserved
    page = (
        vault_root
        / "wiki"
        / "ai-security-research"
        / "clippings"
        / "2026-09-05-AI-Security-Research.md"
    )
    page_text = page.read_text(encoding="utf-8")
    assert "type: clipping" in page_text
    assert "topic: ai-security-research" in page_text
    assert "Body line 1." in page_text

    # Source moved to processed/
    assert not src.exists()
    assert (vault_root / "Clippings" / "processed" / "2026-09-05-AI-Security-Research.md").exists()


def test_process_clippings_appends_wiki_map_row(vault_root: Path, fixed_now) -> None:
    _write_clipping(
        vault_root,
        "ai_security_research.md",
        "# AI Security\n\n…\n",
    )
    process_clippings(vault_root, now=fixed_now, dry_run=False)
    map_md = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert "[[wiki/ai-security/README|ai-security]]" in map_md


def test_process_clippings_groups_multiple_clippings_same_topic(
    vault_root: Path, fixed_now
) -> None:
    _write_clipping(vault_root, "a.md", "# AI Security\n\nBody A.\n")
    _write_clipping(vault_root, "b.md", "# AI Security\n\nBody B.\n")
    result = process_clippings(vault_root, now=fixed_now, dry_run=False)

    assert len(result.processed) == 2
    # Both clippings live under the same topic dir.
    pages_dir = vault_root / "wiki" / "ai-security" / "clippings"
    assert (pages_dir / "a.md").exists()
    assert (pages_dir / "b.md").exists()
    # README created once.
    assert (vault_root / "wiki" / "ai-security" / "README.md").exists()


def test_process_clippings_splits_different_topics(vault_root: Path, fixed_now) -> None:
    _write_clipping(vault_root, "x.md", "# Topic A\n\n…\n")
    _write_clipping(vault_root, "y.md", "# Topic B\n\n…\n")
    process_clippings(vault_root, now=fixed_now, dry_run=False)
    assert (vault_root / "wiki" / "topic-a" / "README.md").exists()
    assert (vault_root / "wiki" / "topic-b" / "README.md").exists()


def test_process_clippings_excludes_processed_dir(vault_root: Path, fixed_now) -> None:
    # Pre-populate processed/ — must not be re-processed.
    proc = vault_root / "Clippings" / "processed"
    proc.mkdir(parents=True)
    (proc / "already.md").write_text("# Already Processed\n\nold.\n", encoding="utf-8")

    # Plus one fresh one to process.
    _write_clipping(vault_root, "fresh.md", "# Fresh\n\nnew.\n")

    result = process_clippings(vault_root, now=fixed_now, dry_run=False)
    processed_sources = {c.source.name for c in result.processed}
    assert "fresh.md" in processed_sources
    assert "already.md" not in processed_sources
    # already.md's body is unchanged (no new wiki entry for it).
    assert not (vault_root / "wiki" / "already-processed").exists()


def test_process_clippings_filename_collision_in_processed(
    vault_root: Path, fixed_now
) -> None:
    # Two files with the same basename ("a.md") under different timestamps.
    (vault_root / "Clippings" / "processed").mkdir(parents=True, exist_ok=True)
    (vault_root / "Clippings" / "processed" / "a.md").write_text("old", encoding="utf-8")
    _write_clipping(vault_root, "a.md", "# Topic\n\n…\n")
    result = process_clippings(vault_root, now=fixed_now, dry_run=False)

    # The new file did NOT clobber the existing processed/a.md.
    assert (vault_root / "Clippings" / "processed" / "a.md").read_text(encoding="utf-8") == "old"
    # And it landed at a unique path inside processed/.
    moved_to = Path(result.processed[0].moved_to)
    assert moved_to.parent == vault_root / "Clippings" / "processed"
    assert moved_to.name != "a.md"
    assert moved_to.exists()


def test_process_clippings_dry_run_makes_no_changes(
    vault_root: Path, fixed_now
) -> None:
    src = _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")
    result = process_clippings(vault_root, now=fixed_now, dry_run=True)

    assert len(result.processed) == 1  # plan is reported
    assert src.exists()  # file NOT moved
    assert not (vault_root / "wiki").exists()  # no wiki created
    # SKILL.md advertises dry-run as side-effect-free: `Clippings/processed/`
    # must NOT be created on a dry run (it would otherwise leak an empty
    # directory into the vault on every dry-run invocation).
    assert not (vault_root / "Clippings" / "processed").exists()


def test_process_clippings_is_idempotent(vault_root: Path, fixed_now) -> None:
    _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")
    r1 = process_clippings(vault_root, now=fixed_now, dry_run=False)
    assert len(r1.processed) == 1

    # Second run: nothing left in Clippings/ top level → processed==[].
    r2 = process_clippings(vault_root, now=fixed_now, dry_run=False)
    assert r2.processed == []


def test_process_clippings_creates_wiki_map_template_when_missing(
    vault_root: Path, fixed_now
) -> None:
    assert not (vault_root / "wiki-map.md").exists()
    _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")
    process_clippings(vault_root, now=fixed_now, dry_run=False)
    text = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert "type: wiki-map" in text
    assert "## Topics" in text
    assert "obsidian-organize:wiki-map:auto-start" in text
    assert "obsidian-organize:wiki-map:auto-end" in text


# ---------- regression tests for /dev-kit:review + /dev-kit:security findings (PR #5) ---


def test_extract_topic_slug_rejects_dot_only_traversal() -> None:
    """CRITICAL (A01 Broken Access Control): a filename whose stem
    normalizes to nothing (e.g. "..") must never produce a topic slug
    of literal dots — `wiki/../` resolves to the vault root itself,
    escaping the intended `wiki/<topic>/` sandbox entirely.
    """
    for filename in ("..", ".", "...", "____"):
        slug = extract_topic_slug("no heading, plain body", filename)
        assert set(slug) != {"."}, f"filename {filename!r} produced dot-only slug {slug!r}"
        resolved = resolve_topic_dir(Path("/vault"), slug)
        assert resolved != Path("/vault"), f"filename {filename!r} escaped to vault root"
        assert resolved.parent == Path("/vault/wiki")


def test_extract_topic_slug_rejects_markdown_hostile() -> None:
    """MAJOR 1 (markdown / wikilink / HTML injection): a last-resort slug
    interpolated into a wikilink `[[wiki/<topic>/README|<topic>]]` and
    a `# <topic>` heading must never smuggle markdown-hostile
    characters. These are the chars that, if left in, would either
    break the link / heading markup or allow HTML / wikilink payloads
    to render in Obsidian.
    """
    for filename in (
        "<script>.md",
        "a]b.md",
        "a[b.md",
        "a|b.md",
        "*star*.md",
        "`code`.md",
        "#hash.md",
        "!bang.md",
        "&amp.md",
        "(paren).md",
        "<img src=x onerror=alert(1)>.md",
        "[link](http://evil).md",
    ):
        slug = extract_topic_slug("no heading, plain body\n", filename)
        # None of the markdown-hostile chars survive.
        for bad in ("<", ">", "|", "[", "]", "(", ")", "*", "`", "#", "!", "&"):
            assert bad not in slug, (
                f"filename {filename!r} produced slug {slug!r} "
                f"containing markdown-hostile char {bad!r}"
            )
        # The slug still resolves INSIDE `wiki/`, never up or out.
        resolved = resolve_topic_dir(Path("/vault"), slug)
        assert resolved.parent == Path("/vault/wiki")


def test_process_clippings_dot_only_stem_stays_inside_wiki(
    vault_root: Path, fixed_now
) -> None:
    """End-to-end: a clipping whose stem is dot-only must land inside
    `wiki/<safe-topic>/`, never directly under the vault root.

    "_.. .md" is a real filename with suffix == ".md" (so it reaches the
    driver's candidate scan), does NOT start with "." (so the dotfile
    filter doesn't exclude it), and has stem == "_.. " — zero
    alphanumerics, so `normalize_topic_slug` returns empty and this
    reaches the last-resort branch that used to leak literal dots.
    """
    _write_clipping(vault_root, "_.. .md", "no heading, plain body\n")
    result = process_clippings(vault_root, now=fixed_now, dry_run=False)
    assert len(result.processed) == 1
    topic_readme = result.processed[0].topic_readme
    assert topic_readme.parent.parent == vault_root / "wiki"
    assert topic_readme.exists()


def test_process_clippings_wiki_map_failure_leaves_source_unmoved(
    vault_root: Path, fixed_now, monkeypatch
) -> None:
    """MAJOR (A10 Exceptional Conditions): if the wiki-map append fails,
    the source clipping must still be sitting in Clippings/ afterward —
    NOT moved to processed/ — so a re-run can retry it instead of
    silently losing the clipping (the previous rename-before-append
    ordering made this data loss permanent).
    """
    import importlib

    # `process_clippings` does `from .bootstrap import append_wiki_map_row`,
    # so patching the bootstrap module attribute doesn't affect the
    # name already bound inside `_lib.process_clippings`. Patch the
    # process_clippings module's own binding.
    pc_module = importlib.import_module("_lib.process_clippings")

    src = _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")

    def _boom(*args, **kwargs):
        raise OSError("simulated disk-full mid wiki-map write")

    monkeypatch.setattr(pc_module, "append_wiki_map_row", _boom)

    with pytest.raises(RuntimeError, match="wiki-map"):
        process_clippings(vault_root, now=fixed_now, dry_run=False)

    # The source was NOT moved into processed/ — it's still retryable.
    assert src.exists()
    assert not (vault_root / "Clippings" / "processed" / "x.md").exists()


def test_wiki_map_write_is_atomic_no_partial_file(vault_root: Path, fixed_now) -> None:
    """MAJOR (A10): the wiki-map write must go through a temp file +
    os.replace, never a partial/truncated file visible mid-write. We
    can't easily simulate a real SIGKILL mid-write in a unit test, but
    we can assert no stray temp file is left behind after a normal run
    (proves the temp-file is renamed away, not just written in place).
    """
    _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")
    process_clippings(vault_root, now=fixed_now, dry_run=False)
    leftover_tmp = list(vault_root.glob(".wiki-map.md.*.tmp"))
    assert leftover_tmp == [], f"temp file(s) left behind: {leftover_tmp}"
    assert (vault_root / "wiki-map.md").exists()


def test_unique_processed_path_same_second_double_collision(tmp_path: Path) -> None:
    """MAJOR (code review #3 — archive-name disambiguation): even if the
    *timestamped* candidate is also already taken (two clippings sharing
    a basename processed within the same wall-clock second), the
    function must keep disambiguating instead of returning an occupied
    path.
    """
    (tmp_path / "a.md").touch()
    first = unique_processed_path(tmp_path, "a.md")
    first.touch()  # simulate: this timestamped name is now also taken
    second = unique_processed_path(tmp_path, "a.md")
    assert second != first
    assert not second.exists()
    assert second.name.startswith("a-")


def test_process_clippings_skips_dotfiles(vault_root: Path, fixed_now) -> None:
    """MINOR (code review — dotfile skip rule, SKILL.md:54): a dotfile
    like `.hidden.md` must not be treated as a clipping to process.
    """
    (vault_root / "Clippings").mkdir(exist_ok=True)
    (vault_root / "Clippings" / ".hidden.md").write_text("# Hidden\n", encoding="utf-8")
    result = process_clippings(vault_root, now=fixed_now, dry_run=False)
    assert result.processed == []
    assert (vault_root / "Clippings" / ".hidden.md").exists()  # left untouched


def test_process_clippings_reuses_bootstrap_wiki_map_template(
    vault_root: Path, fixed_now
) -> None:
    """MAJOR (code review — wiki-map contract duplication): process_clippings
    must seed wiki-map.md using the SAME template/markers as `bootstrap`,
    not a locally-duplicated copy that can drift out of sync.
    """
    from _lib.bootstrap import WIKI_MAP_AUTO_END, WIKI_MAP_AUTO_START

    _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")
    process_clippings(vault_root, now=fixed_now, dry_run=False)
    text = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert WIKI_MAP_AUTO_START in text
    assert WIKI_MAP_AUTO_END in text


def test_wiki_map_append_is_idempotent_on_rename_failure(
    vault_root: Path, fixed_now, monkeypatch
) -> None:
    """MINOR 6: if the wiki-map row was appended but `src.rename`
    fails afterward, a re-run of process_clippings on the same input
    must NOT duplicate the row in wiki-map.md — idempotent append is
    what makes the rename-after-append ordering retry-safe.
    """
    src = _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")
    real_rename = Path.rename

    def _rename_once(self, target):
        # First call (the real run) fails; second call (the re-run)
        # succeeds so we can verify the row is not duplicated.
        if _rename_once.calls == 0:
            _rename_once.calls += 1
            raise OSError("simulated rename failure")
        return real_rename(self, target)

    _rename_once.calls = 0
    monkeypatch.setattr(Path, "rename", _rename_once)

    # First run: wiki-map row appended, rename fails → RuntimeError.
    with pytest.raises(RuntimeError, match="archive"):
        process_clippings(vault_root, now=fixed_now, dry_run=False)

    # Wiki-map row IS present (the append succeeded before rename failed).
    text = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert "[[wiki/topic/README|topic]]" in text
    rows_before = text.count("[[wiki/topic/README|topic]]")
    assert rows_before == 1

    # Second run: append is now idempotent, rename succeeds.
    process_clippings(vault_root, now=fixed_now, dry_run=False)
    text_after = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert text_after.count("[[wiki/topic/README|topic]]") == 1
    assert not src.exists()  # source archived on re-run


def test_wiki_map_creation_threads_now_parameter(vault_root: Path) -> None:
    """MINOR 8: when process_clippings seeds wiki-map.md for the first
    time, the `created:` frontmatter field must reflect the `now`
    parameter — otherwise the deterministic timestamp in tests (and
    real callers using a fixed `now`) leaks into a wall-clock value
    and breaks reproducibility.
    """
    from datetime import datetime, timezone

    fixed = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
    _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")
    process_clippings(vault_root, now=fixed, dry_run=False)
    text = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert "created: 2026-09-05T12:00:00Z" in text


def test_process_clippings_missing_vault_root_raises(
    tmp_path: Path, fixed_now
) -> None:
    """MINOR 5: a missing vault_root must surface as a distinct error
    (so the documented 'Set OBSIDIAN_VAULT or pass --vault <path>'
    message is reachable from the helper) — not silently return the
    same empty result as a missing Clippings/ directory.
    """
    nonexistent = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError, match="Set OBSIDIAN_VAULT"):
        process_clippings(nonexistent, now=fixed_now, dry_run=False)


def test_safe_filename_strips_markdown_hostile_chars() -> None:
    """MINOR 4: `_safe_filename` must strip markdown-hostile chars
    (` * ~ _ [ ] | # `) in addition to the filesystem-hostile set, so
    a hostile filename cannot break a backtick inline-code span (in
    `wiki-map.md`) or smuggle markdown / wikilink / HTML payloads.
    """
    from _lib.paths import safe_filename

    # Each entry: (input, must NOT contain these chars after sanitization).
    cases = [
        ("a`b`c.md", set("`")),
        ("*star*.md", {"*"}),
        ("~tilde~.md", {"~"}),
        ("snake_case.md", set()),  # _ is allowed in plain filenames; the
                                   # wiki-map row is where this matters.
        ("[brackets].md", {"[", "]"}),
        ("hash#tag.md", {"#"}),
        ("pipe|char.md", {"|"}),
        ("`code`.md", set("`")),
    ]
    for raw, forbidden in cases:
        out = safe_filename(raw)
        for ch in forbidden:
            assert ch not in out, (
                f"safe_filename({raw!r}) = {out!r} still contains {ch!r}"
            )
        # The file extension is preserved.
        assert out.endswith(".md"), f"safe_filename({raw!r}) = {out!r} lost extension"


def test_wiki_map_row_sanitizes_hostile_source_filename(
    vault_root: Path, fixed_now
) -> None:
    """MINOR 4 (end-to-end): `bootstrap.append_wiki_map_row`
    interpolates the source filename into a backtick inline-code span.
    A hostile filename (containing backticks / `*` / `_` / `[]` / `|`
    / `#`) must not break the row or leak as raw markdown. The
    sanitized form replaces each hostile char with `-` so the row
    parses as a single inline-code token and the markdown renders
    correctly in Obsidian.
    """
    _write_clipping(vault_root, "evil`name`*_#[1].md", "# Topic\n\nbody\n")
    process_clippings(vault_root, now=fixed_now, dry_run=False)

    text = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    # The original hostile filename does NOT appear verbatim —
    # backticks would have closed the inline-code span, breaking the row.
    assert "evil`name" not in text
    # The sanitized form (every hostile char collapsed to '-') IS present.
    # Extract just the new row (between auto-start and auto-end) and assert
    # the sanitized filename is what's in the backtick span there. We use
    # exact match on the row so the comment-block backticks from the
    # template (`re-running `bootstrap --force...``) don't trip the check.
    row = "- [[wiki/topic/README|topic]] — processed `evil-name-----1-.md`"
    assert row in text, f"sanitized row not found in:\n{text}"


def test_add_wiki_promote_leaves_no_temp_file_leftovers(
    vault_root: Path, fixed_now
) -> None:
    """MAJOR 3: `add_wiki.promote` must route every write through the
    shared `atomic_write_text` helper. After a successful promote,
    no `.<filename>.*.tmp` temp-file leftovers may remain in the
    vault root — proves the helper's temp-file + `os.replace`
    contract holds for the add_wiki code path (add_wiki.py:61,72,79
    in the prior version, which all used bare `path.write_text`).
    """
    from _lib import ResearchInput, promote, write_staged_file

    write_staged_file(
        vault_root,
        ResearchInput(topic="atomic-write", sources=["sources/source-a.md"]),
        now=fixed_now,
    )
    promote(vault_root, "atomic-write", now=fixed_now)

    leftover_tmp = [p for p in vault_root.rglob(".*.tmp")]
    assert leftover_tmp == [], f"temp file(s) left behind: {leftover_tmp}"
    # The promoted topic note + archived staged file both exist.
    assert (vault_root / "topics" / "atomic-write.md").exists()
    assert (vault_root / "_research" / "atomic-write.md").exists()


def test_resolve_clipping_page_uses_safe_filename() -> None:
    """MINOR 4 (helper-level): `resolve_clipping_page` must route the
    filename through the shared `safe_filename` helper so the wiki
    page path can never contain markdown-hostile chars.
    """
    p = resolve_clipping_page(Path("/vault"), "ai-security", "evil`name*.md")
    assert "`" not in p.name
    assert "*" not in p.name


# --------------------------------------------------------------------------- #
# F6 — file-mutation audit gap (PR #5 review)
# --------------------------------------------------------------------------- #


def test_process_clippings_logs_error_on_wiki_map_write_failure(
    vault_root: Path, fixed_now, monkeypatch, caplog
) -> None:
    """F6: a vault-mutating failure must surface via `logger.error`
    (with traceback) BEFORE the `RuntimeError` is raised, so
    post-incident forensics can reconstruct what happened.

    Previously, `process_clippings` wrapped the underlying `OSError`
    in a `RuntimeError` and re-raised with no logging at all — under
    the library's documented default-WARNING contract, the failure
    was invisible to anyone tailing logs at INFO.
    """
    import importlib

    pc_module = importlib.import_module("_lib.process_clippings")

    src = _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")

    def _boom(*args, **kwargs):
        raise OSError("simulated disk-full mid wiki-map write")

    monkeypatch.setattr(pc_module, "append_wiki_map_row", _boom)

    with caplog.at_level(logging.ERROR, logger="_lib.process_clippings"):
        with pytest.raises(RuntimeError, match="wiki-map"):
            process_clippings(vault_root, now=fixed_now, dry_run=False)

    # An ERROR record naming the path was emitted, with exc_info
    # attached (so the traceback is reconstructable from logs).
    error_records = [
        r for r in caplog.records
        if r.levelno == logging.ERROR and "wiki-map" in r.getMessage().lower()
    ]
    assert error_records, (
        f"expected an error log mentioning wiki-map, got: "
        f"{[(r.levelname, r.getMessage()) for r in caplog.records]}"
    )
    assert any(r.exc_info for r in error_records), (
        "expected exc_info=True on at least one error record "
        "(traceback attached)"
    )


def test_process_clippings_logs_error_on_clipping_page_write_failure(
    vault_root: Path, fixed_now, monkeypatch, caplog
) -> None:
    """F6: the clipping-page write failure path must ALSO emit a
    `logger.error` before raising `RuntimeError` — proving the fix is
    applied uniformly to every `raise RuntimeError(...) from e` site
    that wraps a filesystem error, not just the wiki-map one.
    """
    import importlib

    pc_module = importlib.import_module("_lib.process_clippings")

    _write_clipping(vault_root, "y.md", "# Topic\n\n…\n")

    # First `atomic_write_text` call is the topic README — must
    # succeed. Second is the clipping page — must fail. Counting
    # calls lets us trigger the second site specifically.
    real_write_text = pc_module.atomic_write_text
    call_count = {"n": 0}

    def _selective_boom(path, text):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return real_write_text(path, text)  # topic README succeeds
        raise OSError("simulated disk-full mid clipping-page write")

    monkeypatch.setattr(pc_module, "atomic_write_text", _selective_boom)

    with caplog.at_level(logging.ERROR, logger="_lib.process_clippings"):
        with pytest.raises(RuntimeError, match="clipping page"):
            process_clippings(vault_root, now=fixed_now, dry_run=False)

    error_records = [
        r for r in caplog.records
        if r.levelno == logging.ERROR and "clipping page" in r.getMessage().lower()
    ]
    assert error_records, (
        f"expected an error log mentioning clipping page, got: "
        f"{[(r.levelname, r.getMessage()) for r in caplog.records]}"
    )
    assert any(r.exc_info for r in error_records), (
        "expected exc_info=True on at least one error record"
    )