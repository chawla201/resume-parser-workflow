"""SQLAlchemy ORM mapped classes for the candidates and resumes tables."""

from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

_IS_SQLITE: bool = os.getenv("DATABASE_URL", "sqlite:///./dev.db").startswith("sqlite")

# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# Helper: column type aliases that resolve at import time based on DB dialect
# ---------------------------------------------------------------------------

if _IS_SQLITE:
    from sqlalchemy import Text as _UUIDType
    from sqlalchemy import Text as _ArrayType
    from sqlalchemy import Text as _JSONType
else:
    from sqlalchemy.dialects.postgresql import UUID as _PgUUID  # type: ignore[assignment]
    from sqlalchemy.dialects.postgresql import ARRAY, JSONB  # type: ignore[assignment]
    from sqlalchemy import String as _StringType  # noqa: F401

    _UUIDType = _PgUUID(as_uuid=False)  # type: ignore[assignment]
    _ArrayType = ARRAY(Text)  # type: ignore[assignment]
    _JSONType = JSONB  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------


class CandidateRow(Base):
    """ORM model for the ``candidates`` table.

    Attributes:
        id: Primary key UUID (stored as TEXT on SQLite, UUID on Postgres).
        full_name: Candidate's full name. Required.
        email: Contact email address.
        phone: Contact phone number.
        location: Geographic location string.
        linkedin_url: LinkedIn profile URL.
        github_url: GitHub profile URL.
        summary: Professional summary text.
        skills: Serialised skill list (JSON string on SQLite, TEXT[] on Postgres).
        languages: Serialised language list.
        created_at: Row creation timestamp.
        updated_at: Row last-updated timestamp.
        resumes: Back-reference to related ResumeRow records.
    """

    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(
        String(36) if _IS_SQLITE else _UUIDType,
        primary_key=True,
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[str | None] = mapped_column(
        Text if _IS_SQLITE else _ArrayType,
        nullable=True,
    )
    languages: Mapped[str | None] = mapped_column(
        Text if _IS_SQLITE else _ArrayType,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    resumes: Mapped[list[ResumeRow]] = relationship(
        "ResumeRow",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )


class ResumeRow(Base):
    """ORM model for the ``resumes`` table.

    Attributes:
        id: Primary key UUID.
        candidate_id: Foreign key referencing ``candidates.id``.
        raw_text: Full plain-text content of the original resume.
        source_filename: Original uploaded filename.
        json_path: Filesystem path to the written JSON output file.
        education: Serialised education list (JSON string or JSONB).
        experience: Serialised experience list.
        certifications: Serialised certifications list.
        parsed_at: Timestamp when the resume was parsed.
        candidate: Relationship back to the parent CandidateRow.
    """

    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(
        String(36) if _IS_SQLITE else _UUIDType,
        primary_key=True,
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36) if _IS_SQLITE else _UUIDType,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    json_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    education: Mapped[str | None] = mapped_column(
        Text if _IS_SQLITE else _JSONType,
        nullable=True,
    )
    experience: Mapped[str | None] = mapped_column(
        Text if _IS_SQLITE else _JSONType,
        nullable=True,
    )
    certifications: Mapped[str | None] = mapped_column(
        Text if _IS_SQLITE else _JSONType,
        nullable=True,
    )
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candidate: Mapped[CandidateRow] = relationship(
        "CandidateRow",
        back_populates="resumes",
    )
