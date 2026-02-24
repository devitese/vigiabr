"""Base classes for SQLAlchemy ORM models and Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all VigiaBR models."""


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UUIDPrimaryKeyMixin:
    """Mixin that adds a UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class BaseSchema(BaseModel):
    """Pydantic base schema with common configuration."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class BaseEntitySchema(BaseSchema):
    """Base schema for persisted entities (includes id + timestamps)."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
