"""Tests for the interactive reading session key-handling loop."""

import time

from read_habit.timer.session import (
    ReadingSession,
    format_live_status,
    keys_from_sequence,
)
from read_habit.timer.state import ReadingTimer, TimerState


def make_clock(start: float = 0.0):
    state = {"now": start}

    def clock() -> float:
        return state["now"]

    return clock


def test_session_basic_flow_stops_and_returns_stats():
    read_key = keys_from_sequence(["\r", " ", " ", "\r"])
    timer = ReadingTimer(clock=make_clock())
    session = ReadingSession(read_key=read_key, timer=timer, echo=lambda *_: None)

    stats = session.run()

    assert timer.state is TimerState.STOPPED
    assert stats.pages_read == 2


def test_session_ignores_invalid_keys_in_current_state():
    # Space before start is ignored (not started); 'k' before start is
    # ignored too; Enter starts; 'k' pauses; space while paused is
    # ignored; 'k' resumes; Enter stops.
    read_key = keys_from_sequence([" ", "k", "\r", "k", " ", "k", "\r"])
    timer = ReadingTimer(clock=make_clock())
    session = ReadingSession(read_key=read_key, timer=timer, echo=lambda *_: None)

    stats = session.run()

    assert timer.state is TimerState.STOPPED
    assert stats.pages_read == 0


def test_session_pause_resume_cycle():
    read_key = keys_from_sequence(["\r", "k", "k", " ", "\r"])
    timer = ReadingTimer(clock=make_clock())
    session = ReadingSession(read_key=read_key, timer=timer, echo=lambda *_: None)

    stats = session.run()

    assert stats.pages_read == 1


def test_format_live_status_idle():
    timer = ReadingTimer(clock=make_clock())
    status = format_live_status(timer, width=40)
    assert "Elapsed time: 0m 0s" in status
    assert "Actual time: 0m 0s" in status
    assert "current page: 1" in status
    assert "WAITING TO START" in status


def test_format_live_status_running_and_paused():
    clock = make_clock()
    timer = ReadingTimer(clock=clock)
    timer.start()
    status = format_live_status(timer, width=40)
    assert "Elapsed time:" in status
    assert "current page: 1" in status
    assert "READING" in status
    assert "PAUSED" not in status

    timer.pause()
    paused_status = format_live_status(timer, width=40)
    assert "PAUSED" in paused_status


def test_format_live_status_includes_book_title():
    timer = ReadingTimer(clock=make_clock())
    status = format_live_status(timer, book_title="Dune", width=40)
    assert "Dune" in status


def test_format_live_status_centers_lines():
    timer = ReadingTimer(clock=make_clock())
    status = format_live_status(timer, width=40)
    lines = status.split("\n")
    assert all(len(line) == 40 for line in lines)


def test_default_render_overwrites_block_without_scrolling(capsys):
    # The default renderer must write the status block so that repeated
    # calls overwrite the same lines instead of scrolling new ones each
    # tick: it moves the cursor up to the start of the previous block
    # before rewriting, and clears each line before writing new content.
    timer = ReadingTimer(clock=make_clock())
    session = ReadingSession(
        read_key=keys_from_sequence([]),
        timer=timer,
        echo=lambda *_: None,
    )

    session._default_render("line one\nline two")
    first = capsys.readouterr().out
    assert "\x1b[" in first  # uses cursor/clear escape sequences
    assert first.count("\n") == 2

    session._default_render("line one\nline two")
    second = capsys.readouterr().out
    # Moves the cursor up before rewriting the same number of lines.
    assert "\x1b[2A" in second


def test_live_display_renders_status_updates_while_running():
    read_key = keys_from_sequence(["\r", " ", "\r"])
    rendered: list[str] = []
    session = ReadingSession(
        read_key=read_key,
        timer=ReadingTimer(),
        echo=lambda *_: None,
        live_display=True,
        tick_seconds=0.01,
        render_live_status=rendered.append,
    )

    session.run()
    # give the ticker thread a brief chance to render at least once.
    time.sleep(0.05)

    assert len(rendered) >= 1
    assert any("Elapsed time:" in line for line in rendered)
