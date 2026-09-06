"""Regression tests for .github/workflows/_verdict_from_comment.py.

The helper recovers a review/security verdict from PR comments when
extract-verdict.py returns the PARSE_FAILED sentinel. Its selection
order is security-relevant: picking the wrong comment can report a
green gate for a Changes-Requested review.

The bug these tests lock down: the helper's docstring claimed it
sorted matching comments newest-first ("sort defensively so the FIRST
matching comment is the latest one") but no sort existed. Because
`gh pr view --json comments` returns comments OLDEST-first, the helper
returned the oldest post-cutoff verdict. Observed on PR #5 / run
34045860905: a terse `Verdict: Approve` comment at 17:27:18 beat the
real `Verdict: Changes Requested` summary at 17:28:22, and the
severity gate reported pass for a Changes-Requested review.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HELPER = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "_verdict_from_comment.py"
)


def run_helper(comments: list[dict], cutoff: str | None = None) -> str:
    """Invoke the helper as CI does: JSON array on stdin, verdict on stdout."""
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin"}
    if cutoff is not None:
        env["VERDICT_COMMENT_CUTOFF"] = cutoff
    proc = subprocess.run(
        [sys.executable, str(HELPER)],
        input=json.dumps(comments),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, f"helper exited {proc.returncode}: {proc.stderr}"
    return proc.stdout.strip()


def claude(body: str, created_at: str) -> dict:
    return {"body": body, "createdAt": created_at, "author": {"login": "claude"}}


def test_helper_exists() -> None:
    assert HELPER.is_file(), f"helper not found at {HELPER}"


def test_newest_verdict_wins_on_oldest_first_payload() -> None:
    """The exact PR #5 false-Approve timeline must resolve to the real verdict.

    Payload order is oldest-first, matching `gh pr view --json comments`.
    """
    comments = [
        claude("Verdict: Approve", "2026-09-06T17:27:18Z"),
        claude(
            "Verdict: Changes Requested\n\n## Review summary\nreal body",
            "2026-09-06T17:28:22Z",
        ),
    ]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == "Changes Requested"


def test_newest_verdict_wins_regardless_of_payload_order() -> None:
    """Selection must not depend on input ordering at all."""
    older = claude("Verdict: Approve", "2026-09-06T17:27:18Z")
    newer = claude("Verdict: Blocked", "2026-09-06T17:28:22Z")
    for payload in ([older, newer], [newer, older]):
        assert run_helper(payload, "2026-09-06T17:20:45Z") == "Blocked"


def test_a_later_approve_still_wins() -> None:
    """The fix must not bias toward severity -- newest wins, either way.

    A genuine re-review that upgrades Changes Requested to Approve has
    to be honoured, otherwise the gate would never go green after a fix.
    """
    comments = [
        claude("Verdict: Changes Requested", "2026-09-06T17:27:18Z"),
        claude("Verdict: Approve", "2026-09-06T17:28:22Z"),
    ]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == "Approve"


def test_cutoff_still_excludes_stale_verdicts() -> None:
    """Newest-first must not resurrect a pre-cutoff comment (issue #244)."""
    comments = [claude("Verdict: Approve", "2026-09-06T10:00:00Z")]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == ""


def test_non_claude_authors_are_ignored() -> None:
    comments = [
        {
            "body": "Verdict: Approve",
            "createdAt": "2026-09-06T17:28:22Z",
            "author": {"login": "github-actions"},
        }
    ]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == ""


def test_bold_markdown_verdict_is_recognized() -> None:
    comments = [claude("**Verdict:** Blocked", "2026-09-06T17:28:22Z")]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == "Blocked"


def test_undatable_comment_does_not_crash_the_scan() -> None:
    """A comment with no parseable createdAt must not abort the gate."""
    comments = [
        {"body": "Verdict: Approve", "createdAt": "not-a-date", "author": {"login": "claude"}},
        claude("Verdict: Changes Requested", "2026-09-06T17:28:22Z"),
    ]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == "Changes Requested"


def test_no_verdict_anywhere_returns_empty() -> None:
    """Empty output is what makes the gate hard-fail; it must be preserved."""
    comments = [claude("just a comment, no verdict line", "2026-09-06T17:28:22Z")]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == ""


@pytest.mark.parametrize("payload", ["[]", ""])
def test_empty_payload_returns_empty(payload: str) -> None:
    proc = subprocess.run(
        [sys.executable, str(HELPER)],
        input=payload,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
