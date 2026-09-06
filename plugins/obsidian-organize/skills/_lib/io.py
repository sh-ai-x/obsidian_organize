"""Filesystem I/O helpers shared across the plugin's skills.

Currently home to `atomic_write_text` — a temp-file + `os.replace`
write that every write path (`add_wiki`, `remove_wiki`, `research`,
`frontmatter`, `process_clippings`, `bootstrap`) goes through so a
crash or SIGKILL mid-write can never leave a target file truncated
or corrupted.

Public API
----------
- `atomic_write_text(path, text)` — atomically write `text` to `path`.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, text: str) -> None:
    """Write `text` to `path` atomically via temp-file + `os.replace`.

    `os.fdopen` can raise (e.g. invalid encoding on this platform);
    if it raises, the raw file descriptor returned by `mkstemp` would
    leak. Wrap the `os.fdopen` call so we always close the raw fd on
    the error path before re-raising.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        try:
            f = os.fdopen(fd, "w", encoding="utf-8")
        except BaseException:
            # os.fdopen failed before taking ownership of `fd`; close
            # the raw fd ourselves so it doesn't leak.
            os.close(fd)
            raise
        with f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise