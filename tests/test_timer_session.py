"""Tests for the interactive reading session key-handling loop."""

from read_habit.timer.session import ReadingSession, keys_from_sequence
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
