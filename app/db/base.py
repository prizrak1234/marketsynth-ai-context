"""Shared SQLModel base types and mixins."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapper
from sqlalchemy import event
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    now = datetime.now(UTC)
    from app.core.config import get_settings

    if get_settings().database_url.startswith("postgresql"):
        return now.replace(tzinfo=None)
    return now


def utcnow_naive() -> datetime:
    """UTC now without tzinfo — PostgreSQL TIMESTAMP WITHOUT TIME ZONE writes."""
    return datetime.now(UTC).replace(tzinfo=None)


def ensure_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def align_postgres_enum_columns() -> None:
    """Align ORM enum columns with Alembic VARCHAR storage (PostgreSQL only)."""
    from app.core.config import get_settings

    if not get_settings().database_url.startswith("postgresql"):
        return

    from sqlmodel.main import default_registry

    for mapper in default_registry.mappers:
        for column in mapper.columns:
            enum_type = column.type
            if isinstance(enum_type, SAEnum) and enum_type.native_enum:
                column.type = SAEnum(
                    enum_type.enum_class,
                    native_enum=False,
                    values_callable=lambda members: [member.value for member in members],
                    validate_strings=enum_type.validate_strings,
                )


@event.listens_for(Mapper, "mapper_configured")
def _align_enum_columns_with_varchar_storage(mapper: Mapper, class_: type) -> None:
    """Alembic stores enums as VARCHAR; avoid PG native enum casts at runtime."""
    from app.core.config import get_settings

    if not get_settings().database_url.startswith("postgresql"):
        return
    for column in mapper.columns:
        enum_type = column.type
        if isinstance(enum_type, SAEnum) and enum_type.native_enum:
            column.type = SAEnum(
                enum_type.enum_class,
                native_enum=False,
                values_callable=lambda members: [member.value for member in members],
                validate_strings=enum_type.validate_strings,
            )


class UUIDPrimaryKeyMixin(SQLModel):
    """Primary key aligned with contracts (UUID)."""

    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)


class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
