#!/usr/bin/env python3
"""Stop-hook helper: saves the AI chat transcript into the submission's logs/ folder.

Invoked automatically by the Claude Code / Codex Stop hook after each turn.
Output: logs/<tool>/<session_id>.jsonl  (tool = claude-code | codex).
You do not need to run or edit this file.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

_CODEX_CONV_EVENTS = ("user_message", "agent_message")
_CODEX_SYSTEM_PREFIXES = ("<permissions", "<environment_context", "<user_instructions")

_INVALID_BRANCH_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_branch(name: str) -> str:
    """Map a git ref name to a filesystem-safe single-segment directory label.

    - empty / ``.`` / ``..`` / ``/`` → ``"detached"`` (caller didn't get a usable ref).
    - any char outside ``[A-Za-z0-9._/-]`` → ``-`` (so ``feature/foo`` → ``feature-foo``).
    - leading/trailing ``-`` stripped.
    - length capped at 120 chars (path-length safety).
    """
    if not name or name in (".", "..", "/"):
        return "detached"
    cleaned = _INVALID_BRANCH_CHARS.sub("-", name).strip("-")
    if not cleaned:
        return "detached"
    return cleaned[:120]


def detect_branch(cwd: str) -> str:
    """Return a filesystem-safe branch label for ``cwd``, or ``"no-git"``.

    Order of preference:
      1. ``git -C <cwd> symbolic-ref --short -q HEAD``  (attached HEAD → real branch name)
      2. ``git -C <cwd> rev-parse --abbrev-ref HEAD``   (returns ``"HEAD"`` if detached)
         → fall back to ``f"detached-<short-sha>"`` via ``rev-parse --short HEAD``
      3. any failure (``git`` missing, not a repo, timeout) → ``"no-git"``

    Never raises — a logging failure must never block the participant's session.
    """
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "symbolic-ref", "--short", "-q", "HEAD"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            return _sanitize_branch(out.stdout.strip())

        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        if out.returncode == 0:
            ref = out.stdout.strip()
            if ref == "HEAD":
                sha = subprocess.run(
                    ["git", "-C", cwd, "rev-parse", "--short", "HEAD"],
                    capture_output=True, text=True, timeout=2, check=False,
                ).stdout.strip()
                return _sanitize_branch(f"detached-{sha}" if sha else "detached")
            return _sanitize_branch(ref)
        return "no-git"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "no-git"


def _content_text(content) -> str:
    """message content (str or block list) -> conversation text only.

    Ignores tool_use/tool_result/thinking blocks, so a line carrying only those
    yields "" (and is dropped). Used to decide whether a line is real conversation.
    """
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [b["text"] for b in content
                 if isinstance(b, dict) and b.get("type") == "text"
                 and isinstance(b.get("text"), str)]
        return "\n".join(parts).strip()
    return ""


def _claude_has_text(obj) -> bool:
    """True if a claude-code line is a real user/assistant turn carrying conversation text.

    Skips isMeta lines: claude-code injects slash-command output (e.g. /context),
    local-command stdout, and system reminders as user messages flagged isMeta=true —
    these are not conversation and can be huge (a /context dump is ~17KB).
    """
    if not isinstance(obj, dict) or obj.get("type") not in ("user", "assistant"):
        return False
    if obj.get("isMeta"):
        return False
    message = obj.get("message")
    return isinstance(message, dict) and bool(_content_text(message.get("content")))


def _codex_has_event_text(obj) -> bool:
    """True if a codex line is a user_message/agent_message event with text."""
    if not isinstance(obj, dict) or obj.get("type") != "event_msg":
        return False
    payload = obj.get("payload")
    if not isinstance(payload, dict) or payload.get("type") not in _CODEX_CONV_EVENTS:
        return False
    message = payload.get("message")
    return isinstance(message, str) and bool(message.strip())


def _codex_has_response_text(obj) -> bool:
    """True if a codex response_item carries conversation text (fallback when no event_msg)."""
    if not isinstance(obj, dict) or obj.get("type") != "response_item":
        return False
    payload = obj.get("payload")
    if not isinstance(payload, dict) or payload.get("role") not in ("user", "assistant"):
        return False
    text = _content_text(payload.get("content"))
    return bool(text) and not text.lstrip().startswith(_CODEX_SYSTEM_PREFIXES)


def slim_transcript(raw: str, tool: str):
    """Keep only the conversation lines from a transcript, verbatim, as JSONL.

    Drops lines that carry no user/assistant conversation text — tool calls/results,
    thinking/reasoning, session metadata, skill listings. Kept lines are the original
    JSONL lines unchanged, so the output stays valid JSONL in the source schema.
    Returns None when nothing parses or no conversation line is found, so the caller
    falls back to copying the transcript verbatim. Unparseable lines are skipped.
    """
    pairs, any_parsed = [], False
    for line in raw.split("\n"):
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except (ValueError, TypeError):
            continue
        any_parsed = True
        pairs.append((line, obj))
    if not any_parsed:
        return None
    if tool == "codex":
        kept = [line for line, obj in pairs if _codex_has_event_text(obj)]
        if not kept:                            # fallback: response_item (no event_msg present)
            kept = [line for line, obj in pairs if _codex_has_response_text(obj)]
    else:
        kept = [line for line, obj in pairs if _claude_has_text(obj)]
    if not kept:
        return None
    return "\n".join(kept) + "\n"


def main() -> int:
    # Never write to stdout — Codex parses Stop-hook stdout as a decision.
    # Always exit 0 so a logging failure never blocks the participant's session.
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True, choices=["claude-code", "codex"])
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
    except Exception as exc:  # noqa: BLE001 - non-fatal
        print(f"save_log: failed to parse stdin JSON: {exc}", file=sys.stderr)
        return 0

    transcript_path = payload.get("transcript_path")
    cwd = payload.get("cwd") or os.getcwd()
    session_id = payload.get("session_id") or "session"

    if not transcript_path or not os.path.isfile(transcript_path):
        print(
            f"save_log: transcript_path missing or not a file: {transcript_path!r}",
            file=sys.stderr,
        )
        return 0

    safe_session = os.path.basename(str(session_id))
    if safe_session in ("", ".", ".."):
        safe_session = "session"
    branch = detect_branch(cwd)
    dest_dir = os.path.join(cwd, "logs", args.tool, branch)
    dest = os.path.join(dest_dir, f"{safe_session}.jsonl")

    # Save only conversation lines; fall back to a verbatim copy on any doubt.
    try:
        os.makedirs(dest_dir, exist_ok=True)
        with open(transcript_path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        slim = slim_transcript(raw, args.tool)
        if slim is None:
            shutil.copyfile(transcript_path, dest)
        else:
            with open(dest, "w", encoding="utf-8") as out:
                out.write(slim)
    except Exception as exc:  # noqa: BLE001 - non-fatal
        print(f"save_log: trim failed, copying verbatim: {exc}", file=sys.stderr)
        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copyfile(transcript_path, dest)
        except Exception as exc2:  # noqa: BLE001 - non-fatal
            print(f"save_log: copy failed: {exc2}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
