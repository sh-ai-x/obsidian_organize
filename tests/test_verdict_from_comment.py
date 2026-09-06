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

Second security regression (F1, #625 security review): author
matching used `startswith('claude')`, so any GitHub account whose
login merely started with "claude" (`claude-evil`, `claudefan`,
`Claude-Attacker`) was treated as the official Claude bot. A
spoofing account could post `Verdict: Approve` and flip the severity
gate green, overriding the real agent verdict. The regression tests
in this file pin identity to GitHub's bot-authentication contract:
`user.type == "Bot"` AND (`user.login` in TRUSTED_AUTHOR_LOGINS
OR `performed_via_github_app.slug` in TRUSTED_APP_SLUGS). The shell
script fetches from the REST endpoint so those raw fields reach the
helper (the legacy `gh pr view --json comments` source strips the
`[bot]` suffix and drops `performed_via_github_app`).
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


# Payload shape mirrors `gh api /repos/{owner}/{repo}/issues/{n}/comments`:
#   {user: {login: "claude[bot]", type: "Bot"}, performed_via_github_app:
#   {slug: "claude"}, body, created_at (snake_case)}.
def claude(body: str, created_at: str) -> dict:
    """A comment from the genuine Claude GitHub App -- trusted."""
    return {
        "body": body,
        "created_at": created_at,
        "user": {"login": "claude[bot]", "type": "Bot"},
        "performed_via_github_app": {"slug": "claude"},
    }


def test_helper_exists() -> None:
    assert HELPER.is_file(), f"helper not found at {HELPER}"


def test_newest_verdict_wins_on_oldest_first_payload() -> None:
    """The exact PR #5 false-Approve timeline must resolve to the real verdict.

    Payload order is oldest-first, matching the order the REST endpoint
    returns per page. The newest-first sort in the helper still has to win.
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
    """A plain human account is not a trusted author."""
    comments = [
        {
            "body": "Verdict: Approve",
            "created_at": "2026-09-06T17:28:22Z",
            "user": {"login": "github-actions", "type": "User"},
        }
    ]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == ""


def test_bold_markdown_verdict_is_recognized() -> None:
    comments = [claude("**Verdict:** Blocked", "2026-09-06T17:28:22Z")]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == "Blocked"


def test_undatable_comment_does_not_crash_the_scan() -> None:
    """A comment with no parseable timestamp must not abort the gate."""
    comments = [
        {
            "body": "Verdict: Approve",
            "created_at": "not-a-date",
            "user": {"login": "claude[bot]", "type": "Bot"},
            "performed_via_github_app": {"slug": "claude"},
        },
        claude("Verdict: Changes Requested", "2026-09-06T17:28:22Z"),
    ]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == "Changes Requested"


def test_no_verdict_anywhere_returns_empty() -> None:
    """Empty output is what makes the gate hard-fail; it must be preserved."""
    comments = [claude("just a comment, no verdict line", "2026-09-06T17:28:22Z")]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == ""


# ------------------------------------------------------------------
# Spoofing regression tests (F1, #625 security review).
#
# The previous `_is_claude_author` used `login.lower().startswith("claude")`,
# so any GitHub account named "claude-evil", "claudefan",
# "Claude-Attacker", or even a User account literally named "claude[bot]"
# was accepted as the legitimate Claude bot. A `Verdict: Approve` from
# any such account would flip the severity gate green.
#
# The strict check requires `user.type == "Bot"` AND
# (`user.login` in {"claude[bot]"} OR
#  `performed_via_github_app.slug` in {"claude"}).
# ------------------------------------------------------------------


def _spoof_comment(login: str, body: str = "Verdict: Approve") -> dict:
    """Build a comment shaped like a spoofing attempt: human User account."""
    return {
        "body": body,
        "created_at": "2026-09-06T17:28:22Z",
        "user": {"login": login, "type": "User"},
    }


@pytest.mark.parametrize("login", ["claude-evil", "claudefan", "Claude-Attacker"])
def test_spoof_logins_with_user_type_are_ignored(login: str) -> None:
    """Human-controlled accounts whose login merely resembles "claude"
    must NOT be treated as the legitimate Claude bot. The pre-fix
    startswith('claude') check would have accepted all of these and
    flipped the gate green on a `Verdict: Approve`."""
    comments = [_spoof_comment(login)]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == ""


def test_user_account_with_claude_bot_login_is_ignored() -> None:
    """A human User account whose login is literally `claude[bot]`
    must be ignored -- type must be Bot, not User. Pre-fix this would
    have been accepted (login starts with 'claude') and could spoof
    verdicts."""
    comments = [_spoof_comment("claude[bot]")]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == ""


def test_genuine_bot_comment_is_accepted() -> None:
    """The minimum-shape legitimate Claude bot comment must be accepted."""
    comments = [
        {
            "body": "Verdict: Approve",
            "created_at": "2026-09-06T17:28:22Z",
            "user": {"login": "claude[bot]", "type": "Bot"},
        }
    ]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == "Approve"


def test_app_slug_trusted_with_bot_type_is_accepted() -> None:
    """Comments written via the registered `claude` GitHub App must be
    accepted even when `user.login` is the raw app name without the
    `[bot]` suffix -- the slug allowlist pins identity to the app
    registration, which GitHub cannot impersonate."""
    comments = [
        {
            "body": "Verdict: Approve",
            "created_at": "2026-09-06T17:28:22Z",
            "user": {"login": "some-app-bot-name", "type": "Bot"},
            "performed_via_github_app": {"slug": "claude"},
        }
    ]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == "Approve"


def test_app_slug_without_bot_type_is_ignored() -> None:
    """Defensive: `performed_via_github_app.slug` alone is not enough
    -- a spoofing attempt that fabricates the slug field but has
    `user.type == "User"` must still be rejected."""
    comments = [
        {
            "body": "Verdict: Approve",
            "created_at": "2026-09-06T17:28:22Z",
            "user": {"login": "attacker", "type": "User"},
            "performed_via_github_app": {"slug": "claude"},
        }
    ]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == ""


def test_spoofing_does_not_shadow_real_verdict() -> None:
    """A spoofed `Verdict: Approve` must not override a real
    `Verdict: Changes Requested` from the genuine bot. Pre-fix the
    gate would have reported green for a Changes-Requested review."""
    comments = [
        _spoof_comment("claude-evil"),
        claude("Verdict: Changes Requested", "2026-09-06T17:28:22Z"),
    ]
    assert run_helper(comments, "2026-09-06T17:20:45Z") == "Changes Requested"


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
