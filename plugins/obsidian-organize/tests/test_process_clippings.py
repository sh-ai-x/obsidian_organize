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


def test_extract_topic_slug_from_filename_when_no_h1() -> None:
    text = "no heading here, just prose"
    assert extract_topic_slug(text, "LangChain_Research_2026-09-05.md") == "langchain-research-2026-09-05"


def test_extract_topic_slug_handles_non_ascii() -> None:
    # Korean / mixed-script headings collapse to a slug-friendly form; if the
    # result is empty (no ASCII chars survived), fall back to the filename.
    text = "# 한경 보안 리서치\n\n"
    slug = extract_topic_slug(text, "한국_보안_리서치.md")
    assert slug == "한국-보안-리서치" or slug == "한국-보안-리서치"


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
    assert not (vault_root / "wiki").exists()


def test_process_clippings_single_clipping_creates_wiki_entry(
    vault_root: Path, fixed_now
) -> None:
    src = _write_clipping(
        vault_root,
        "2026-09-05_AI_Security_Research.md",
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
        / "2026-09-05_AI_Security_Research.md"
    )
    page_text = page.read_text(encoding="utf-8")
    assert "type: clipping" in page_text
    assert "topic: ai-security-research" in page_text
    assert "Body line 1." in page_text

    # Source moved to processed/
    assert not src.exists()
    assert (vault_root / "Clippings" / "processed" / "2026-09-05_AI_Security_Research.md").exists()


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

    # `import _lib.process_clippings as x` would resolve to the
    # re-exported *function* of the same name in _lib/__init__.py
    # (attribute-access collision), not the submodule — go through
    # importlib to get the actual submodule object unambiguously.
    pc_module = importlib.import_module("_lib.process_clippings")

    src = _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")

    def _boom(*args, **kwargs):
        raise OSError("simulated disk-full mid wiki-map write")

    monkeypatch.setattr(pc_module, "_append_wiki_map_row", _boom)

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