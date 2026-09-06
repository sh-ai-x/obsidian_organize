#!/usr/bin/env bash
# _verdict_comments_fallback.sh — PR-comments retry-loop fallback (issue #625).
#
# Single source of truth for the retry-loop that recovers the agent's
# verdict from a PR comment authored by the verified Claude GitHub App
# when extract-verdict.py returned PARSE_FAILED. ("claude-prefixed"
# author matching was the F1 spoofing vulnerability -- see the endpoint
# note below.) Previously this loop was copy-pasted between
# the review and security jobs (review.yml lines 419-441 and 749-771);
# the duplication was flagged by the #625 review (F1, retry-loop
# SSOT violation). Both jobs now call this script with different
# JOB_NAME labels so the ::notice:: / ::warning:: lines distinguish
# the call site.
#
# Contract:
#   in : $1 = PR_NUMBER
#        CUTOFF  (env, ISO-8601 timestamp — only newer comments count)
#        JOB_NAME (env, label for ::notice:: / ::warning:: lines)
#        WORKSPACE (env, default $GITHUB_WORKSPACE)
#   out: prints the recovered verdict to stdout (empty if no match)
#        ::notice:: / ::warning:: diagnostics go to STDERR so the
#        captured ``$(script "$PR_NUMBER")`` value is exactly the
#        verdict word — review.yml L418 / L727 write that value to
#        ``$GITHUB_OUTPUT`` and the severity gate parses it as a
#        single token. Mixing diagnostics into stdout would corrupt
#        the verdict variable with the diagnostic blob.
#
# The jq selector is intentionally minimal — `[.[] | {body, created_at,
# user, performed_via_github_app}]` — so the Python helper is the
# single source of truth for author matching. The shell script only
# shapes the payload; strict identity verification
# (`user.type == "Bot"` AND allowlisted `user.login` /
# `performed_via_github_app.slug`) lives in `_is_claude_author` so
# author logic stays in one place.
#
# Endpoint note (F1, #625 security review): we fetch from
# `gh api /repos/{owner}/{repo}/issues/{n}/comments` rather than
# `gh pr view --json comments` because the latter strips the
# `[bot]` suffix from `author.login` and drops the
# `performed_via_github_app` field -- making the strict-bot-identity
# check impossible. The REST endpoint exposes the raw GitHub payloads
# with `user.type`, `user.login` (including the `[bot]` suffix), and
# `performed_via_github_app.slug` intact. `--paginate` is required
# because the endpoint caps each page at 100 comments and a PR can
# have more than that across its lifetime.
set -euo pipefail

PR_NUMBER="${1:?usage: $0 <PR_NUMBER>}"
# PR_NUMBER must be an integer — the REST path interpolates it directly
# and a non-integer would either 404 or silently produce an empty
# comments payload (making the script's "no verdict recovered" path
# indistinguishable from a transient gh failure). Validate before use.
case "$PR_NUMBER" in
  ''|*[!0-9]*) echo "::error::${JOB_NAME:-review} PR_NUMBER must be an integer: got '$PR_NUMBER'" >&2; exit 64 ;;
esac
CUTOFF="${CUTOFF:-}"
JOB_NAME="${JOB_NAME:-review}"
WORKSPACE="${WORKSPACE:-${GITHUB_WORKSPACE:-$(pwd)}}"

# Retry budget. The original 6 x 5s (30s) was sized against an assumed
# ~30s async window for claude-code-action to post the agent's verdict
# comment. Measured on run 34048314595 the real latency was ~3 minutes:
# the security job's extract step gave up and posted
# `verdict=PARSE_FAILED source=parse-failed-no-verdict` at 17:24:01,
# while the agent's verdict comment did not land until 17:27:18 --
# 197s later. A 30s budget therefore cannot observe a comment that
# arrives on the normal path, so the gate hard-failed a clean review.
#
# 24 x 10s = 240s covers the measured 197s with headroom. This is a
# correctly-sized wait for an asynchronous publish, NOT a threshold
# raised to make a failing step pass: the loop still exits empty (and
# the gate still hard-fails) when no verdict comment ever appears.
ATTEMPTS="${ATTEMPTS:-24}"
SLEEP_SECONDS="${SLEEP_SECONDS:-10}"
HELPER="${WORKSPACE}/.github/workflows/_verdict_from_comment.py"

comment_verdict=""
# Per-attempt scratch file for gh stderr — captured from the SAME
# `gh api` call that produces the comments payload, so the
# diagnostics and the data are guaranteed to come from one fetch
# (previously two separate calls could disagree if a transient error
# happened between them, producing a ghost warning with no payload).
gh_err_file="$(mktemp)"
helper_err_file="$(mktemp)"
trap 'rm -f "$gh_err_file" "$helper_err_file"' EXIT
# Owner/repo is required by the REST endpoint path
# `/repos/{owner}/{repo}/issues/{n}/comments`. Prefer the
# GITHUB_REPOSITORY env var (set on every Actions run); fall back to
# `gh repo view` for local invocations and tests. If both fail we
# still proceed -- the gh call will error out per attempt and the
# retry loop will exhaust, producing the same "no verdict recovered"
# outcome as a transient failure.
if [ -n "${GITHUB_REPOSITORY:-}" ]; then
  owner_repo="$GITHUB_REPOSITORY"
else
  owner_repo=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null || echo "")
fi
if [ -z "$owner_repo" ]; then
  echo "::warning::${JOB_NAME} cannot derive owner/repo for gh api fallback (GITHUB_REPOSITORY unset and gh repo view failed)" >&2
fi
for attempt in $(seq 1 "$ATTEMPTS"); do
  echo "::notice::${JOB_NAME} PR-comments fallback attempt=${attempt}/${ATTEMPTS}" >&2
  : >"$gh_err_file"
  comments_json=$(gh api --paginate "/repos/${owner_repo}/issues/${PR_NUMBER}/comments" \
    --jq '[.[] | {body, created_at, user, performed_via_github_app}]' \
    2>"$gh_err_file") || true
  gh_err=$(cat "$gh_err_file")
  if [ -n "$gh_err" ]; then
    echo "::warning::${JOB_NAME} gh api stderr (attempt=${attempt}): ${gh_err}" >&2
  fi
  if [ -n "$comments_json" ]; then
    # Nit n2: the helper's stderr used to be sent to /dev/null, so a
    # broken helper (SyntaxError, ImportError, a crash on an odd
    # comment object) burned the whole retry loop silently and surfaced
    # only the generic "fallback exhausted" warning. Capture it and
    # promote it to a ::warning:: so CI shows the real cause.
    : >"$helper_err_file"
    comment_verdict=$(printf '%s' "$comments_json" \
      | VERDICT_COMMENT_CUTOFF="$CUTOFF" python3 "$HELPER" 2>"$helper_err_file" \
      || true)
    helper_err=$(cat "$helper_err_file")
    if [ -n "$helper_err" ]; then
      echo "::warning::${JOB_NAME} _verdict_from_comment.py stderr (attempt=${attempt}): ${helper_err}" >&2
    fi
    if [ -n "$comment_verdict" ]; then
      break
    fi
  fi
  [ "$attempt" -lt "$ATTEMPTS" ] && sleep "$SLEEP_SECONDS"
done

if [ -n "$comment_verdict" ]; then
  echo "::notice::${JOB_NAME} verdict recovered from PR comments: ${comment_verdict}" >&2
else
  echo "::warning::${JOB_NAME} PR-comments fallback exhausted after ${ATTEMPTS} attempts" >&2
fi

# Stdout MUST carry only the verdict word (empty on exhaustion). The
# call sites use ``$(script "$PR_NUMBER")`` so any extra line on stdout
# corrupts the captured value.
printf '%s' "$comment_verdict"
