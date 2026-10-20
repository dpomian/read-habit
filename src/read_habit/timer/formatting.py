"""Formatting helpers for presenting reading timer statistics."""

from __future__ import annotations

from read_habit.timer.models import PageRecord, TimerStats


def _format_seconds(seconds: float) -> str:
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes}m {secs}s"


def format_stats(stats: TimerStats) -> str:
    """Render final session statistics as a human-readable block."""
    lines = [
        "Reading session summary:",
        f"  Pages read:          {stats.pages_read}",
        f"  Slowest page:        {_format_page(stats.slowest_page)}",
        f"  Fastest page:        {_format_page(stats.fastest_page)}",
        f"  Actual reading time: {_format_seconds(stats.actual_reading_seconds)}",
        f"  Elapsed time:        {_format_seconds(stats.elapsed_seconds)}",
        f"  Paused for:          {_format_seconds(stats.paused_seconds)}",
    ]
    return "\n".join(lines)


def _format_page(record: PageRecord | None) -> str:
    if record is None:
        return "n/a"
    return f"page {record.page_number} ({_format_seconds(record.duration_seconds)})"
