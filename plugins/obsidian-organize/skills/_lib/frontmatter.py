"""Frontmatter read/write for the staged research and topic notes.

Format: YAML between `---` fences at the top of the file. The body is
preserved verbatim. Values are returned as a plain `dict` so callers can
mutate them and re-serialize.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import atomic_write_text

FrontmatterDict = dict[str, Any]

_FENCE = "---"


def parse_frontmatter(text: str) -> tuple[FrontmatterDict, str]:
    """Split a markdown file into (frontmatter dict, body string).

    If the file has no frontmatter, returns ({}, original_text).
    """
    if not text.startswith(f"{_FENCE}\n"):
        return {}, text

    end = text.find(f"\n{_FENCE}\n", len(_FENCE))
    if end == -1:
        return {}, text

    fm_block = text[len(_FENCE) + 1 : end]
    body = text[end + len(_FENCE) + 2 :]
    fm = _parse_simple_yaml(fm_block)
    return fm, body


def serialize_frontmatter(fm: FrontmatterDict, body: str) -> str:
    """Render frontmatter + body back to a complete markdown file."""
    fm_block = _serialize_simple_yaml(fm)
    if not fm_block:
        return body
    return f"{_FENCE}\n{fm_block}{_FENCE}\n{body}"


def update_frontmatter_field(
    path: Path, updates: FrontmatterDict
) -> FrontmatterDict:
    """Read, merge `updates` into the file's frontmatter, return the new dict.

    Writes the merged result back to `path`. Returns the merged dict.
    """
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    fm.update(updates)
    atomic_write_text(path, serialize_frontmatter(fm, body))
    return fm


# --- minimal YAML subset for our frontmatter --------------------------------
# We support the keys/values we actually emit, no nested anchors, no flow
# style. Lists are block-style (`- item`). Strings are emitted as bare,
# quoted (if they contain special chars), or block scalars.


def _parse_simple_yaml(block: str) -> FrontmatterDict:
    lines = block.splitlines()
    result: FrontmatterDict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if not line.startswith((" ", "\t")) and ":" in line:
            key, _, rest = line.partition(":")
            key = key.strip()
            rest = rest.strip()
            if rest == "":
                # Either a nested mapping or a list. Look ahead.
                children, consumed = _parse_block(lines, i + 1)
                result[key] = children
                i += 1 + consumed
            elif rest.startswith("[") and rest.endswith("]"):
                # inline flow list, e.g. tags: [topic/foo]
                inner = rest[1:-1]
                items = [_coerce(x.strip()) for x in _split_flow(inner)]
                result[key] = items
                i += 1
            else:
                result[key] = _coerce(rest)
                i += 1
        else:
            i += 1
    return result


def _parse_block(lines: list[str], start: int) -> tuple[Any, int]:
    """Parse an indented block. Returns (parsed value, lines consumed)."""
    # Detect list vs mapping.
    if start >= len(lines) or not lines[start].startswith((" ", "\t")):
        return None, 0
    first = lines[start].lstrip()
    if first.startswith("- "):
        items: list[Any] = []
        i = start
        while i < len(lines) and lines[i].startswith((" ", "\t")):
            stripped = lines[i].lstrip()
            if not stripped.startswith("- "):
                break
            items.append(_coerce(stripped[2:].strip()))
            i += 1
        return items, i - start
    # Mapping
    mapping: FrontmatterDict = {}
    i = start
    while i < len(lines) and lines[i].startswith((" ", "\t")):
        stripped = lines[i].lstrip()
        if ":" not in stripped:
            i += 1
            continue
        key, _, rest = stripped.partition(":")
        mapping[key.strip()] = _coerce(rest.strip())
        i += 1
    return mapping, i - start


def _split_flow(inner: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    in_str: str | None = None
    for ch in inner:
        if in_str:
            buf.append(ch)
            if ch == in_str and (len(buf) < 2 or buf[-2] != "\\"):
                in_str = None
            continue
        if ch in ('"', "'"):
            in_str = ch
            buf.append(ch)
            continue
        if ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return parts


def _coerce(s: str) -> Any:
    s = s.strip()
    if not s:
        return ""
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    if s.lower() in ("null", "~"):
        return None
    return s


def _serialize_simple_yaml(fm: FrontmatterDict) -> str:
    out: list[str] = []
    for k, v in fm.items():
        if isinstance(v, list):
            if not v:
                out.append(f"{k}: []")
            else:
                out.append(f"{k}:")
                for item in v:
                    out.append(f"  - {_quote(str(item))}")
        elif isinstance(v, dict):
            out.append(f"{k}:")
            for kk, vv in v.items():
                out.append(f"  {kk}: {_quote(str(vv))}")
        elif v is None:
            out.append(f"{k}: null")
        elif isinstance(v, bool):
            out.append(f"{k}: {'true' if v else 'false'}")
        else:
            out.append(f"{k}: {_quote(str(v))}")
    if not out:
        return ""
    return "\n".join(out) + "\n"


def _quote(s: str) -> str:
    if not s:
        return '""'
    needs = any(c in s for c in [":", "#", '"', "'", "\n", "[", "]", "{", "}"])
    if not needs:
        return s
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
