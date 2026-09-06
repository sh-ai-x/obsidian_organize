"""Tests for `obsidian-organize:bootstrap`."""

from __future__ import annotations

import multiprocessing as mp
import sys
from pathlib import Path

from _lib.bootstrap import bootstrap


def test_bootstrap_creates_canonical_layout(vault_root, fixed_now):
    result = bootstrap(vault_root, now=fixed_now)

    assert (vault_root / "Clippings").is_dir()
    assert (vault_root / "Clippings" / "processed").is_dir()
    assert (vault_root / "Clippings" / ".keep").exists()
    assert (vault_root / "Clippings" / "processed" / ".keep").exists()
    assert (vault_root / "wiki").is_dir()
    assert (vault_root / "wiki" / ".keep").exists()
    assert (vault_root / "_research").is_dir()
    assert (vault_root / "_research" / ".keep").exists()
    assert (vault_root / "_archive" / "research").is_dir()
    assert (vault_root / "_archive" / "research" / ".keep").exists()
    assert (vault_root / "topics").is_dir()
    assert result.wiki_map_written is True


def test_bootstrap_writes_wiki_map_template_with_markers(vault_root, fixed_now):
    bootstrap(vault_root, now=fixed_now)

    text = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "type: wiki-map" in text
    assert "obsidian-organize:wiki-map:auto-start" in text
    assert "obsidian-organize:wiki-map:auto-end" in text
    assert "# Wiki Map" in text
    assert "## Topics" in text


def test_bootstrap_seeds_topic_subdirs_when_requested(vault_root, fixed_now):
    result = bootstrap(
        vault_root,
        topics=["Hermes Protocol", "wire-protocols"],
        now=fixed_now,
    )

    assert "hermes-protocol" in result.seeded_topics
    assert "wire-protocols" in result.seeded_topics
    for slug in ("hermes-protocol", "wire-protocols"):
        d = vault_root / "wiki" / slug
        assert d.is_dir()
        assert (d / ".keep").exists()
        readme = d / "README.md"
        assert readme.exists()
        body = readme.read_text(encoding="utf-8")
        assert f"topic: {slug}" in body
        assert "seeded-by: bootstrap" in body


def test_bootstrap_refuses_to_clobber_existing_layout(vault_root, fixed_now):
    bootstrap(vault_root, now=fixed_now)
    sentinel = vault_root / "wiki" / "user-note.md"
    sentinel.write_text("do not delete me", encoding="utf-8")

    bootstrap(vault_root, now=fixed_now)
    assert sentinel.exists()
    assert sentinel.read_text(encoding="utf-8") == "do not delete me"


def test_bootstrap_force_overwrites(vault_root, fixed_now):
    bootstrap(vault_root, now=fixed_now)
    (vault_root / "wiki-map.md").unlink()
    result = bootstrap(vault_root, force=True, now=fixed_now)
    assert result.wiki_map_written is True
    assert (vault_root / "wiki-map.md").exists()


# --------------------------------------------------------------------------- #
# F2 — wiki-map.md TOCTOU / lost-update fix (PR #5 review)
# --------------------------------------------------------------------------- #


def _concurrent_append_worker(args: tuple[int, str, "mp.synchronize.Barrier"]) -> None:
    """Subprocess target for the F2 concurrent-append test.

    Module-level so `spawn`-based multiprocessing can pickle it.
    Each worker waits on a shared barrier so all N processes hit the
    read-modify-write window simultaneously, then calls
    `append_wiki_map_row` with a topic name unique to this worker.
    Without the flock, the last writer clobbers every prior writer's
    appended row (lost update).
    """
    i, vault_root_str, barrier = args
    sys.path.insert(0, str(_SKILLS_DIR))
    from _lib.bootstrap import append_wiki_map_row  # noqa: WPS433
    barrier.wait()  # Synchronise the start of the read-modify-write.
    append_wiki_map_row(
        Path(vault_root_str), f"topic-{i}", f"source-{i}.md"
    )


_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def test_append_wiki_map_row_concurrent_no_lost_updates(tmp_path: Path) -> None:
    """F2: concurrent appends to wiki-map.md must not lose rows.

    Without `fcntl.flock(LOCK_EX)` guarding the read-modify-write in
    `append_wiki_map_row`, two processes can both read the same
    snapshot of `wiki-map.md`, both append a distinct row to their
    in-memory copy, and the second `atomic_write_text` clobbers the
    first's appended row. The atomic write only prevents partial
    writes — it does NOT prevent stale-snapshot overwrites.

    Spawning multiple real processes (each appending a distinct row
    to the same wiki-map.md) and asserting every row is present is
    the proof. A barrier synchronises the start of the read so the
    race window is reliably hit. The test MUST fail (missing rows)
    when the lock is removed.
    """
    vault_root = tmp_path
    bootstrap(vault_root)  # Seed wiki-map.md with the template.

    n = 8
    ctx = mp.get_context()  # platform default (spawn on macOS, fork on Linux)
    barrier = ctx.Barrier(n)

    args_list = [(i, str(vault_root), barrier) for i in range(n)]
    procs = [ctx.Process(target=_concurrent_append_worker, args=(a,)) for a in args_list]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)
        assert not p.is_alive(), f"subprocess {p.name} timed out"
        assert p.exitcode == 0, f"subprocess {p.name} exited with code {p.exitcode}"

    text = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    missing = [
        i for i in range(n)
        if f"[[wiki/topic-{i}/README|topic-{i}]]" not in text
    ]
    assert not missing, (
        f"lost updates detected for topics {missing}; "
        f"wiki-map.md contents:\n{text}"
    )
