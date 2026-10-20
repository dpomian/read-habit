"""Formatting helpers for presenting reading timer statistics."""

from __future__ import annotations

import shutil

from read_habit.timer.models import PageRecord, TimerStats

DEFAULT_DISPLAY_WIDTH = 80


def format_seconds(seconds: float) -> str:
    """Render a duration in seconds as ``"<minutes>m <seconds>s"``."""
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes}m {secs}s"


def _display_width() -> int:
    """Return the width to center the live session display within.

    Falls back to :data:`DEFAULT_DISPLAY_WIDTH` when the terminal size
    cannot be determined (e.g. when output is not a real terminal).
    """
    return shutil.get_terminal_size(fallback=(DEFAULT_DISPLAY_WIDTH, 24)).columns


def center_block(lines: list[str], width: int | None = None) -> str:
    """Center each of ``lines`` within ``width`` columns and join them."""
    if width is None:
        width = _display_width()
    return "\n".join(line.center(width) for line in lines)


def format_session_display(
    book_title: str | None,
    status_label: str,
    elapsed_seconds: float,
    actual_seconds: float,
    current_page: int,
    page_seconds: float,
    width: int | None = None,
    book_author: str | None = None,
) -> str:
    """Render the full, centered live session layout.

    Produces the multi-line block described in the feature request: a
    title line naming the book (and author, if any), the current status,
    the running elapsed/actual times, the control reminders, and the
    current page with its own elapsed time. The whole block is centered
    line by line so it stays nicely aligned in the terminal.
    """
    if book_title and book_author:
        title = f"New reading session for '{book_title}', by {book_author}"
    elif book_title:
        title = f"New reading session for '{book_title}'"
    else:
        title = "New reading session"
    lines = [
        title,
        "",
        f"=== {status_label} ===",
        "",
        f"Elapsed time: {format_seconds(elapsed_seconds)}",
        f"Actual time: {format_seconds(actual_seconds)}",
        "",
        "=== controls ===",
        "start/stop: enter",
        "pause/resume: k",
        "next page: space",
        "-----------------",
        "",
        f"current page: {current_page}  time: {format_seconds(page_seconds)}",
    ]
    return center_block(lines, width=width)


def format_stats(stats: TimerStats) -> str:
    """Render final session statistics as a human-readable block."""
    lines = [
        "Reading session summary:",
        f"  Pages read:          {stats.pages_read}",
        f"  Slowest page:        {_format_page(stats.slowest_page)}",
        f"  Fastest page:        {_format_page(stats.fastest_page)}",
        f"  Actual reading time: {format_seconds(stats.actual_reading_seconds)}",
        f"  Elapsed time:        {format_seconds(stats.elapsed_seconds)}",
        f"  Paused for:          {format_seconds(stats.paused_seconds)}",
    ]
    return "\n".join(lines)


def _format_page(record: PageRecord | None) -> str:
    if record is None:
        return "n/a"
    return f"page {record.page_number} ({format_seconds(record.duration_seconds)})"
