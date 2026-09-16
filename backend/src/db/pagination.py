"""Shared pagination helper (offset/limit) per research.md.

Default page size 50, max 200, page 1-indexed.
"""

from __future__ import annotations

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def normalize_pagination(page: int | None, page_size: int | None) -> tuple[int, int]:
    """Return (page, pageSize) clamped to safe bounds."""
    normalized_page = page if page and page > 0 else DEFAULT_PAGE
    normalized_page_size = page_size if page_size and page_size > 0 else DEFAULT_PAGE_SIZE
    normalized_page_size = min(normalized_page_size, MAX_PAGE_SIZE)
    return normalized_page, normalized_page_size


def offset_for(page: int, page_size: int) -> int:
    return (page - 1) * page_size
