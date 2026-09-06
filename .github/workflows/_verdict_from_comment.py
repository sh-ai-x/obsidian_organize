#!/usr/bin/env python3
"""_verdict_from_comment.py — fallback verdict extractor from PR comments.

Used by templates/ci/.github/workflows/review.yml when the agent's
output file (claude-execution-output.json) exists but cannot be parsed
into a verdict (extract-verdict.py returns the PARSE_FAILED sentinel --
issue #625). Some providers (e.g. minimax) return a wrapper-format
output envelope that the parser cannot read, but the agent still
posts an `mcp__github_file_ops__create_comment` summary as a PR
comment with a `Verdict: <Word>` line. This helper recovers the
verdict from that comment.

Single-source-of-truth note: VERDICT_RE is mirrored from
`templates/ci/scripts/extract-verdict.py:70` -- same regex, same
match group. Duplicated rather than imported because extract-verdict.py
runs in a different action context that does not have import access
to this helper script.

Why a second regex (VERDICT_RE_LENIENT) lives here: the LLM judges
(review, security, maintenance) post their summary as a PR comment
in Markdown, which wraps the verdict label in bold asterisks
(`**Verdict:** Changes Requested`). The strict extract-verdict.py
regex is correct for the agent's output file (its contract is the
plain form), but PR comments are an LLM-formatted surface where
bold decoration is the norm. This helper therefore uses
VERDICT_RE_LENIENT in the comment-parsing loop and keeps VERDICT_RE
strict for documentation parity with the gate's primary parser.

Cutoff filter (issue #244 root-cause): only comments strictly newer
than $VERDICT_COMMENT_CUTOFF (ISO 8601) count. The caller passes the
PR head-commit timestamp (PR-mode) or pull_request.updated_at
(workflow_dispatch) -- NOT a fixed clock, so the filter adapts to
the PR lifecycle. Older comments from previous pushes are ignored
to avoid resurrecting stale verdicts (the #244 bug).

Selection order: among the comments that pass the author and cutoff
filters, the NEWEST one wins. The payload arrives oldest-first, so
`main` sorts explicitly rather than trusting input order -- see the
comment on the sort in `main` for the false-Approve this prevents.

Author matching is STRICT. The previous startswith('claude') check
was a CRITICAL vulnerability (F1 from the #625 security review): any
GitHub account whose login merely starts with "claude" — e.g.
"claude-evil", "claudefan", "Claude-Attacker" — was treated as the
legitimate Claude bot, so a `Verdict: Approve` PR comment from any
such account flipped the severity gate green and overrode the real
agent verdict. The check below pins identity to GitHub's bot
authentication contract: a comment counts as the trusted agent only
if `user.type == "Bot"` AND (`user.login` is in TRUSTED_AUTHOR_LOGINS
OR `performed_via_github_app.slug` is in TRUSTED_APP_SLUGS). Those
two allowlists are the trust anchor for this helper; do not widen
them without a security review.

Usage:
    cat comments.json | VERDICT_COMMENT_CUTOFF=2024-01-01T00:00:00Z \\
        python3 _verdict_from_comment.py

Prints the verdict word (Approve | Blocked | Changes Requested) on
stdout, or empty string if no matching comment exists. Exits 0 always
on success (including no-match); exits 2 only on bad usage (no stdin,
invalid JSON, non-array payload).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

# Mirrored from templates/ci/scripts/extract-verdict.py:70.
# Kept for reference; the helper uses VERDICT_RE_LENIENT below to
# recover from bold-form LLM-judge comments (`**Verdict:** <Word>`).
VERDICT_RE = re.compile(r'Verdict:\s*(Approve|Blocked|Changes Requested)\b')
# Lenient variant: tolerates zero/two leading or trailing `*` chars
# around both `Verdict` and the colon (Markdown bold wrapping).
# Anchor `(?:^|\n)` keeps it from matching across line boundaries.
VERDICT_RE_LENIENT = re.compile(
    r'(?:^|\n)\s*\*?\*?Verdict:\*?\*?\s*(Approve|Blocked|Changes Requested)\b'
)
CUTOFF_ENV = "VERDICT_COMMENT_CUTOFF"

# --- Trust anchor for verdict-author spoofing prevention (F1, #625 security review) ---
# GitHub's bot-authentication contract for comments written via a registered
# GitHub App: `user.type == "Bot"`, `user.login == "<app-slug>[bot]"`, and
# `performed_via_github_app.slug == "<app-slug>"`. Pinning identity to these
# exact values rejects any human-controlled account whose login merely
# resembles "claude" (e.g. "claude-evil", "claudefan"). Do not widen either
# allowlist without a security review.
TRUSTED_AUTHOR_LOGINS = frozenset({"claude[bot]"})
TRUSTED_APP_SLUGS = frozenset({"claude"})


def _parse_iso(s: str) -> datetime | None:
    """Parse an ISO 8601 string, accepting the 'Z' suffix.

    Returns None on parse failure so the filter degrades gracefully
    instead of throwing the whole script. Unparseable timestamps
    cause the comment to be EXCLUDED (principle of least surprise:
    a comment we cannot date is treated as stale).
    """
    if not s:
        return None
    text = s.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _comment_created_at(comment: dict) -> str:
    """Return the comment's creation timestamp string.

    The /repos/{owner}/{repo}/issues/{n}/comments endpoint returns
    `created_at` (snake_case); the legacy `gh pr view --json comments`
    returns `createdAt` (camelCase). Accept either so the helper stays
    robust against either payload source.
    """
    if not isinstance(comment, dict):
        return ""
    raw = comment.get("created_at")
    if not isinstance(raw, str):
        raw = comment.get("createdAt", "")
    return raw if isinstance(raw, str) else ""


def _after_cutoff(comment: dict, cutoff: datetime | None) -> bool:
    """True iff comment's creation timestamp is strictly newer than cutoff.

    cutoff=None (no env var set) accepts all comments -- the caller
    is responsible for setting the cutoff when staleness is a concern.
    """
    if cutoff is None:
        return True
    ts = _parse_iso(_comment_created_at(comment))
    if ts is None:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts > cutoff


def _is_claude_author(comment: dict) -> bool:
    """True iff the comment is verified to be from the trusted Claude bot.

    Requires BOTH conditions (strict identity pinning, F1 from #625
    security review -- the previous startswith('claude') check accepted
    any human-controlled account whose login resembled "claude"):

      1. ``user.type == "Bot"`` (case-insensitive), AND
      2. (``user.login`` in TRUSTED_AUTHOR_LOGINS
          OR ``performed_via_github_app.slug`` in TRUSTED_APP_SLUGS)

    Isinstance guards are kept on every attribute access so a malformed
    comment object (missing user, wrong shape, etc.) degrades to
    "not trusted, skip" instead of crashing the gate -- preserves the
    prior behaviour for odd payloads.
    """
    if not isinstance(comment, dict):
        return False
    user = comment.get("user")
    if not isinstance(user, dict):
        return False
    user_type = user.get("type")
    if not isinstance(user_type, str) or user_type.lower() != "bot":
        return False
    login = user.get("login")
    if isinstance(login, str) and login in TRUSTED_AUTHOR_LOGINS:
        return True
    app = comment.get("performed_via_github_app")
    if isinstance(app, dict):
        slug = app.get("slug")
        if isinstance(slug, str) and slug in TRUSTED_APP_SLUGS:
            return True
    return False


def _verdict_from_body(body: str) -> str:
    """Return the verdict word if body contains a recognized Verdict line, else ''.

    Uses VERDICT_RE_LENIENT so bold-wrapped LLM-judge comments
    (`**Verdict:** <Word>`) are recognized in addition to the plain
    `Verdict: <Word>` form.
    """
    if not isinstance(body, str):
        return ""
    m = VERDICT_RE_LENIENT.search(body)
    return m.group(1) if m else ""


def main() -> int:
    if sys.stdin is None or sys.stdin.isatty():
        print(f"usage: {sys.argv[0]} reads JSON comments array from stdin", file=sys.stderr)
        return 2
    raw = sys.stdin.read()
    if not raw.strip():
        print("", end="")
        return 0
    try:
        comments = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"invalid JSON on stdin: {e}", file=sys.stderr)
        return 2
    if not isinstance(comments, list):
        print("stdin must decode to a JSON array of comment objects", file=sys.stderr)
        return 2
    cutoff = _parse_iso(os.environ.get(CUTOFF_ENV, ""))
    # Newest-first. This sort is load-bearing, not defensive polish:
    # `gh pr view --json comments` returns comments OLDEST-first, so
    # iterating the payload as-given returns the oldest post-cutoff
    # verdict. That produced a false `Approve` on a commit whose real
    # review body said `Changes Requested` -- a stray terse
    # `Verdict: Approve` comment predated the real summary by ~1 minute
    # and won. The gate then reported green for a Changes-Requested
    # review, which is the worst possible failure direction for a
    # review gate.
    #
    # Comments that cannot be dated sort last (they are already
    # excluded by `_after_cutoff` whenever a cutoff is set; the
    # `datetime.min` floor only decides their relative order in the
    # no-cutoff case, where oldest-last is still the safer default).
    def _sort_key(c: object) -> datetime:
        ts = _parse_iso(_comment_created_at(c)) if isinstance(c, dict) else None
        if ts is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts

    for c in sorted(comments, key=_sort_key, reverse=True):
        if not _is_claude_author(c):
            continue
        if not _after_cutoff(c, cutoff):
            continue
        verdict = _verdict_from_body(c.get("body", ""))
        if verdict:
            print(verdict)
            return 0
    print("", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
