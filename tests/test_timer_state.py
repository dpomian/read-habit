"""Tests for the reading timer state machine."""

import pytest

from read_habit.timer.state import InvalidTimerTransition, ReadingTimer, TimerState


def make_clock(start: float = 0.0):
    """Return a controllable fake clock and its setter."""
    state = {"now": start}

    def clock() -> float:
        return state["now"]

    def advance(seconds: float) -> None:
        state["now"] += seconds

    return clock, advance


def test_initial_state_is_idle():
    timer = ReadingTimer()
    assert timer.state is TimerState.IDLE


def test_start_transitions_to_running():
    timer = ReadingTimer()
    timer.start()
    assert timer.state is TimerState.RUNNING


def test_cannot_start_twice():
    timer = ReadingTimer()
    timer.start()
    with pytest.raises(InvalidTimerTransition):
        timer.start()


def test_pause_requires_running():
    timer = ReadingTimer()
    with pytest.raises(InvalidTimerTransition):
        timer.pause()


def test_resume_requires_paused():
    timer = ReadingTimer()
    timer.start()
    with pytest.raises(InvalidTimerTransition):
        timer.resume()


def test_finish_page_requires_running():
    timer = ReadingTimer()
    timer.start()
    timer.pause()
    with pytest.raises(InvalidTimerTransition):
        timer.finish_page()


def test_finish_page_not_allowed_before_start():
    timer = ReadingTimer()
    with pytest.raises(InvalidTimerTransition):
        timer.finish_page()


def test_stop_requires_started_timer():
    timer = ReadingTimer()
    with pytest.raises(InvalidTimerTransition):
        timer.stop()


def test_stop_allowed_while_running_or_paused():
    clock, advance = make_clock()
    timer = ReadingTimer(clock=clock)
    timer.start()
    advance(1)
    stats = timer.stop()
    assert timer.state is TimerState.STOPPED
    assert stats.elapsed_seconds == 1

    timer2 = ReadingTimer(clock=clock)
    timer2.start()
    advance(1)
    timer2.pause()
    advance(1)
    stats2 = timer2.stop()
    assert timer2.state is TimerState.STOPPED
    assert stats2.paused_seconds == 1


def test_cannot_act_after_stop():
    timer = ReadingTimer()
    timer.start()
    timer.stop()
    with pytest.raises(InvalidTimerTransition):
        timer.pause()
    with pytest.raises(InvalidTimerTransition):
        timer.resume()
    with pytest.raises(InvalidTimerTransition):
        timer.finish_page()
    with pytest.raises(InvalidTimerTransition):
        timer.stop()


def test_full_session_statistics():
    clock, advance = make_clock()
    timer = ReadingTimer(clock=clock)

    timer.start()
    advance(10)  # page 1 takes 10s
    timer.finish_page()
    advance(5)  # page 2 takes 5s
    timer.pause()
    advance(3)  # 3s paused, should not count as reading time
    timer.resume()
    advance(2)  # finish page 2 after resuming: total page 2 duration 5+2=7s
    timer.finish_page()
    advance(1)
    stats = timer.stop()

    assert stats.pages_read == 3
    assert stats.slowest_page.page_number == 1
    assert stats.slowest_page.duration_seconds == 10
    assert stats.fastest_page.page_number == 3
    assert stats.fastest_page.duration_seconds == 1
    assert stats.paused_seconds == 3
    assert stats.actual_reading_seconds == 10 + 7 + 1
    assert stats.elapsed_seconds == 10 + 5 + 3 + 2 + 1


def test_stop_while_running_counts_the_in_progress_page_as_read():
    """Reproduces #7: stopping mid-page must count that page as read.

    ``actual_reading_seconds`` already includes the time spent on the page
    that was being read when ``stop`` was called, so ``pages_read`` (and
    the fastest/slowest breakdown) must account for it too, instead of
    silently dropping it.
    """
    clock, advance = make_clock()
    timer = ReadingTimer(clock=clock)

    timer.start()
    advance(12)
    timer.finish_page()  # page 1: 12s
    advance(13)
    timer.finish_page()  # page 2: 13s
    advance(3)  # page 3: still being read when we stop
    stats = timer.stop()

    assert stats.pages_read == 3
    assert stats.actual_reading_seconds == 12 + 13 + 3
    assert stats.fastest_page.page_number == 3
    assert stats.fastest_page.duration_seconds == 3
    assert stats.slowest_page.page_number == 2
    assert stats.slowest_page.duration_seconds == 13


def test_fastest_and_slowest_page_identified():
    clock, advance = make_clock()
    timer = ReadingTimer(clock=clock)
    timer.start()
    advance(10)
    timer.finish_page()
    advance(2)
    timer.finish_page()
    advance(5)
    stats = timer.stop()

    assert stats.slowest_page.page_number == 1
    assert stats.slowest_page.duration_seconds == 10
    assert stats.fastest_page.page_number == 2
    assert stats.fastest_page.duration_seconds == 2


def test_current_page_increments_on_finish():
    timer = ReadingTimer()
    timer.start()
    assert timer.current_page == 1
    timer.finish_page()
    assert timer.current_page == 2
