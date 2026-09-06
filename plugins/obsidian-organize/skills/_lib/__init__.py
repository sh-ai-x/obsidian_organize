"""obsidian-organize: implementation helpers for the plugin's skills.

Each skill (research / add_wiki / remove_wiki) is LLM-driven via its
SKILL.md, but the deterministic parts (frontmatter read/write, slug
normalization, back-link scanning, full skill helpers) live here so tests
can exercise them without an LLM in the loop.
"""

from .frontmatter import (
    parse_frontmatter,
    serialize_frontmatter,
    update_frontmatter_field,
    FrontmatterDict,
)
from .io import atomic_write_text
from .slug import normalize_topic_slug, validate_topic_slug
from .paths import (
    resolve_staged_path,
    resolve_topic_path,
    resolve_archive_path,
    safe_filename,
    scan_backlinks,
    BACKLINK_MARKER_TEMPLATE,
)
from .research import (
    ResearchInput,
    ResearchResult,
    write_staged_file,
)
from .add_wiki import (
    AddWikiResult,
    promote,
)
from .remove_wiki import (
    RemoveWikiResult,
    retire,
)
from .process_clippings import (
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

__all__ = [
    # frontmatter
    "parse_frontmatter",
    "serialize_frontmatter",
    "update_frontmatter_field",
    "FrontmatterDict",
    # io
    "atomic_write_text",
    # slug
    "normalize_topic_slug",
    "validate_topic_slug",
    # paths
    "resolve_staged_path",
    "resolve_topic_path",
    "resolve_archive_path",
    "safe_filename",
    "scan_backlinks",
    "BACKLINK_MARKER_TEMPLATE",
    # research
    "ResearchInput",
    "ResearchResult",
    "write_staged_file",
    # add_wiki
    "AddWikiResult",
    "promote",
    # remove_wiki
    "RemoveWikiResult",
    "retire",
    # process_clippings
    "ClippingPage",
    "ProcessClippingsResult",
    "extract_topic_slug",
    "process_clippings",
    "render_clipping_page",
    "render_topic_readme",
    "resolve_clipping_page",
    "resolve_processed_path",
    "resolve_topic_dir",
    "unique_processed_path",
]
