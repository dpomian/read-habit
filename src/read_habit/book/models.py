"""Data models for the book entity."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Book(BaseModel):
    """A book that reading sessions can be linked to."""

    id: int = Field(ge=1)
    title: str = Field(min_length=1)
    author: str | None = None
    total_pages: int | None = Field(default=None, ge=1)
