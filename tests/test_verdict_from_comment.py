"""Tests for .github/workflows/_verdict_from_comment.py.

Covers the PR-comments fallback path that recovers the agent's verdict
when the agent's JSONL execution file is missing or unreadable but the
agent (or a recovery path) posted a verdict as a PR comment.

Author matching is STRICT: the helper accepts only comments authored
by `claude[bot]` (the agent's GitHub App) so a hostile account whose
login merely starts with "claude" cannot flip the gate green. Issue
#612/#625 added a SECOND trust anchor for recovery comments authored
by `github-actions[bot]` with the explicit recovery marker — those
are emitted by review.yml when the agent ran but emitted no parseable
verdict. The marker + author-pin combo prevents forgery.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "_verdict_from_comment.py"


def _run(payload: object, cutoff: str | None = "2024-01-01T00:00:00Z") -> subprocess.CompletedProcess:
    """Run the helper with a JSON payload on stdin and a cutoff env var."""
    env = os.environ.copy()
    if cutoff is not None:
        env["VERDICT_COMMENT_CUTOFF"] = cutoff
    else:
        env.pop("VERDICT_COMMENT_CUTOFF", None)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    # The helper prints `print(verdict)` (newline-terminated) on a hit
    # and `print("", end="")` on no-match. Strip the trailing newline
    # so asserting `result.stdout == "Approve"` reads cleanly — the
    # real caller captures via ``$(...)`` which already strips it.
    proc.stdout = proc.stdout.rstrip("\n")
    return proc


def _comment(
    body: str,
    login: str = "claude[bot]",
    user_type: str = "Bot",
    created_at: str = "2025-01-01T00:00:00Z",
    app_slug: str | None = None,
) -> dict:
    """Build a comment dict with created_at that passes the default cutoff.

    `created_at` defaults to 2025 (after the test's 2024 cutoff) so
    verdict-extraction tests don't have to repeat the date plumbing.
    Tests that explicitly exercise the cutoff filter override this.
    """
    user = {"type": user_type, "login": login}
    comment: dict = {"body": body, "created_at": created_at, "user": user}
    if app_slug is not None:
        comment["performed_via_github_app"] = {"slug": app_slug}
    return comment


# ---------------------------------------------------------------------------
# Author identity — strict trust anchor (F1, #625)
# ---------------------------------------------------------------------------


def test_claude_bot_approved_verdict_is_accepted() -> None:
    result = _run([_comment("Verdict: Approve")])
    assert result.returncode == 0
    assert result.stdout == "Approve"


def test_human_account_with_similar_login_is_rejected() -> None:
    """F1 regression: any login resembling 'claude' must NOT be trusted."""
    result = _run([_comment("Verdict: Approve", login="claude-evil", user_type="User")])
    assert result.returncode == 0
    assert result.stdout == ""


def test_bot_account_with_wrong_login_is_rejected() -> None:
    result = _run([_comment("Verdict: Approve", login="some-other-bot[bot]")])
    assert result.returncode == 0
    assert result.stdout == ""


def test_missing_user_field_is_rejected() -> None:
    result = _run([{"body": "Verdict: Approve", "created_at": "2025-01-01T00:00:00Z"}])
    assert result.returncode == 0
    assert result.stdout == ""


def test_app_slug_can_satisfy_trust_anchor() -> None:
    result = _run([_comment("Verdict: Blocked", app_slug="claude")])
    assert result.returncode == 0
    assert result.stdout == "Blocked"


# ---------------------------------------------------------------------------
# Body shape — VERDICT_RE_LENIENT tolerates bold wrapping
# ---------------------------------------------------------------------------


def test_bold_wrapped_verdict_is_accepted() -> None:
    result = _run([_comment("**Verdict:** Changes Requested")])
    assert result.returncode == 0
    assert result.stdout == "Changes Requested"


def test_verdict_in_middle_of_body_is_accepted() -> None:
    """Anchor `(?:^|\n)` keeps the regex from matching across line boundaries."""
    body = "Some prose above\n\nVerdict: Approve\n\nSome prose below"
    result = _run([_comment(body)])
    assert result.returncode == 0
    assert result.stdout == "Approve"


def test_multiple_verdicts_last_wins() -> None:
    """Newest-first sort + last-match-wins."""
    result = _run(
        [
            _comment("Verdict: Approve", created_at="2025-06-01T00:00:00Z"),
            _comment("Verdict: Blocked", created_at="2025-06-02T00:00:00Z"),
        ]
    )
    assert result.returncode == 0
    assert result.stdout == "Blocked"


# ---------------------------------------------------------------------------
# Cutoff filter — issue #244 stale-comment flap
# ---------------------------------------------------------------------------


def test_stale_comment_before_cutoff_is_rejected() -> None:
    result = _run([_comment("Verdict: Approve", created_at="2020-01-01T00:00:00Z")])
    assert result.returncode == 0
    assert result.stdout == ""


def test_no_cutoff_accepts_all_dated_comments() -> None:
    """When cutoff is unset, all datable comments count (caller decides)."""
    result = _run(
        [_comment("Verdict: Approve", created_at="2020-01-01T00:00:00Z")],
        cutoff=None,
    )
    assert result.returncode == 0
    assert result.stdout == "Approve"


# ---------------------------------------------------------------------------
# Issue #612/#625 recovery path — github-actions[bot] with the marker
# ---------------------------------------------------------------------------


def test_recovery_comment_with_marker_and_correct_author_is_accepted() -> None:
    """The recovery path: synthetic verdict posted by the CI workflow
    when the agent ran but emitted no parseable verdict. The marker
    pins identity to a workflow-emitted comment (not a hostile PR
    comment that happens to contain 'Verdict: Approve')."""
    body = (
        "<!-- dev-kit-verdict-recovery --> run=42 job=review head_sha=deadbeef\n"
        "\n"
        "Verdict: Approve\n"
        "\n"
        "Recovery: the /dev-kit:review agent emitted no parseable verdict."
    )
    result = _run([_comment(body, login="github-actions[bot]")])
    assert result.returncode == 0
    assert result.stdout == "Approve"


def test_recovery_marker_without_marker_is_rejected() -> None:
    """The marker is load-bearing — without it, the github-actions bot
    is just an ordinary audit commenter, not a recovery artifact."""
    result = _run(
        [
            _comment(
                "Verdict: Approve\n\nNo marker here.",
                login="github-actions[bot]",
            )
        ]
    )
    assert result.returncode == 0
    assert result.stdout == ""


def test_recovery_marker_without_github_actions_author_is_rejected() -> None:
    """The author pin is load-bearing — a human account that pastes the
    marker into a PR comment cannot forge a recovery verdict."""
    result = _run(
        [
            _comment(
                "<!-- dev-kit-verdict-recovery --> run=42\nVerdict: Approve",
                login="sh-ai-x",
                user_type="User",
            )
        ]
    )
    assert result.returncode == 0
    assert result.stdout == ""


def test_recovery_marker_with_human_account_claiming_bot_type_is_rejected() -> None:
    """Type-spoofing check: a User account whose `user.type` field is
    forged to "Bot" still must not pass."""
    result = _run(
        [
            _comment(
                "<!-- dev-kit-verdict-recovery -->\nVerdict: Approve",
                login="random-human",
                user_type="Bot",
            )
        ]
    )
    assert result.returncode == 0
    assert result.stdout == ""


def test_recovery_comment_respects_cutoff() -> None:
    """The cutoff filter applies to recovery comments too — a stale
    recovery comment from a previous push cannot resurrect."""
    body = (
        "<!-- dev-kit-verdict-recovery --> run=42\n"
        "Verdict: Approve"
    )
    result = _run(
        [
            _comment(
                body,
                login="github-actions[bot]",
                created_at="2020-01-01T00:00:00Z",
            )
        ]
    )
    assert result.returncode == 0
    assert result.stdout == ""


def test_claude_bot_verdict_takes_precedence_over_recovery() -> None:
    """The agent's own verdict (claude[bot]) is preferred over a
    recovery comment (github-actions[bot]). When both are present and
    both pass the cutoff, the claude[bot] pass wins (it runs first)."""
    claude_body = "Verdict: Changes Requested"
    recovery_body = (
        "<!-- dev-kit-verdict-recovery --> run=99\nVerdict: Approve"
    )
    result = _run(
        [
            _comment(
                recovery_body,
                login="github-actions[bot]",
                created_at="2025-06-02T00:00:00Z",
            ),
            _comment(
                claude_body,
                created_at="2025-06-01T00:00:00Z",
            ),
        ]
    )
    assert result.returncode == 0
    # claude[bot] pass is preferred; recovery is a last-resort fallback
    # only triggered when the agent emitted nothing parseable.
    assert result.stdout == "Changes Requested"


# ---------------------------------------------------------------------------
# Robustness — malformed payloads must not crash the gate
# ---------------------------------------------------------------------------


def test_invalid_json_returns_exit_2() -> None:
    """Bad usage (non-JSON stdin) returns exit 2 so CI sees the error."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input="not json",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2


def test_non_array_payload_returns_exit_2() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input='{"not": "an array"}',
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2


def test_empty_payload_returns_empty_stdout() -> None:
    result = _run([])
    assert result.returncode == 0
    assert result.stdout == ""


def test_missing_body_field_is_skipped() -> None:
    result = _run([{"created_at": "2025-01-01T00:00:00Z", "user": {"type": "Bot", "login": "claude[bot]"}}])
    assert result.returncode == 0
    assert result.stdout == ""


def test_non_string_body_is_skipped() -> None:
    result = _run(
        [{"body": 12345, "created_at": "2025-01-01T00:00:00Z", "user": {"type": "Bot", "login": "claude[bot]"}}]
    )
    assert result.returncode == 0
    assert result.stdout == ""
