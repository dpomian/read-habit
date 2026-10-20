"""Data models for the reading timer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PageRecord(BaseModel):
    """A single page's reading duration."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    duration_seconds: float = Field(ge=0)


class TimerStats(BaseModel):
    """Summary statistics produced when a reading session stops."""

    model_config = ConfigDict(frozen=True)

    pages_read: int = Field(ge=0)
    slowest_page: PageRecord | None = None
    fastest_page: PageRecord | None = None
    actual_reading_seconds: float = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)
    paused_seconds: float = Field(ge=0)
