"""Cross-dialect SQLAlchemy filters for enum columns stored as name or value."""

from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy import String, cast, func, or_
from sqlalchemy.sql.elements import ColumnElement


def enum_member_stored_values(enum_member: Enum | str) -> tuple[str, ...]:
    """Return normalized string forms that may appear in DB for this enum member."""
    if isinstance(enum_member, Enum):
        values: list[str] = []
        if enum_member.value is not None:
            values.append(str(enum_member.value))
        if enum_member.name is not None:
            values.append(str(enum_member.name))
        # De-dupe while preserving order (value first).
        seen: set[str] = set()
        ordered: list[str] = []
        for item in values:
            lowered = item.lower()
            if lowered not in seen:
                seen.add(lowered)
                ordered.append(lowered)
        return tuple(ordered)
    text = str(enum_member).strip()
    lowered = text.lower()
    variants = [lowered]
    if lowered != text:
        variants.append(text.lower())
    return tuple(dict.fromkeys(variants))


def enum_column_equals(column: Any, enum_member: Enum | str) -> ColumnElement[bool]:
    """Match enum column regardless of PostgreSQL/SQLite string representation."""
    stored = enum_member_stored_values(enum_member)
    if not stored:
        return cast(column, String) == str(enum_member)
    comparisons = [func.lower(cast(column, String)) == value for value in stored]
    if len(comparisons) == 1:
        return comparisons[0]
    return or_(*comparisons)


def enum_column_not_equals(column: Any, enum_member: Enum | str) -> ColumnElement[bool]:
    return ~enum_column_equals(column, enum_member)
