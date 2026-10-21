"""Reading timer state machine.

The timer models the following states and transitions, as described in the
feature request:

* ``IDLE``    -- the timer has not started yet.
* ``RUNNING`` -- the timer is actively measuring reading time.
* ``PAUSED``  -- the timer is temporarily stopped; no time accrues.
* ``STOPPED`` -- the session has ended; final statistics are available.

Transitions are only valid from specific states, which is enforced by
raising :class:`InvalidTimerTransition` for any other attempt. In
particular:

* A page can only be marked finished while ``RUNNING`` (not while paused).
* The timer can only be paused while ``RUNNING`` and resumed while
  ``PAUSED``.
* The timer can be stopped from either ``RUNNING`` or ``PAUSED`` ("any
  time"), but not before it has started or after it has already stopped.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from enum import Enum

from read_habit.timer.models import PageRecord, TimerStats


class TimerState(Enum):
    """Possible states of a :class:`ReadingTimer`."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class InvalidTimerTransition(Exception):
    """Raised when an action is attempted from an incompatible state."""


class ReadingTimer:
    """A finite state machine that tracks reading time per page.

    Parameters
    ----------
    clock:
        A zero-argument callable returning the current time in seconds.
        Defaults to :func:`time.monotonic`. Injecting a fake clock makes
        the timer deterministic for tests.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._state = TimerState.IDLE

        self._session_start: float | None = None
        self._session_end: float | None = None

        self._page_number = 1
        self._page_started_at: float | None = None
        self._page_accumulated_seconds = 0.0

        self._actual_reading_seconds = 0.0
        self._paused_seconds = 0.0
        self._pause_started_at: float | None = None

        self._page_records: list[PageRecord] = []

    @property
    def state(self) -> TimerState:
        """Return the current state of the timer."""
        return self._state

    @property
    def current_page(self) -> int:
        """Return the number of the page currently being read."""
        return self._page_number

    def live_elapsed_seconds(self) -> float:
        """Return the elapsed session time so far, including right now.

        Returns ``0.0`` before the timer has started. Once stopped, the
        final elapsed time is returned.
        """
        if self._session_start is None:
            return 0.0
        end = self._session_end if self._session_end is not None else self._clock()
        return end - self._session_start

    def live_page_seconds(self) -> float:
        """Return the current page's reading time so far, including now.

        While ``RUNNING`` this includes the time elapsed since the page
        timer last resumed. While ``PAUSED`` or before the page has
        started, the accumulated (frozen) time is returned.
        """
        if self._state is TimerState.RUNNING and self._page_started_at is not None:
            return self._page_accumulated_seconds + (
                self._clock() - self._page_started_at
            )
        return self._page_accumulated_seconds

    def live_paused_seconds(self) -> float:
        """Return the total paused time so far, including the current pause."""
        paused = self._paused_seconds
        if self._state is TimerState.PAUSED and self._pause_started_at is not None:
            paused += self._clock() - self._pause_started_at
        return paused

    def live_actual_seconds(self) -> float:
        """Return the total actual reading time so far (elapsed minus paused).

        This is the time spent actively reading, excluding any time spent
        paused, up to and including right now.
        """
        return self.live_elapsed_seconds() - self.live_paused_seconds()

    def start(self) -> None:
        """Start the timer. Only valid from ``IDLE``."""
        if self._state is not TimerState.IDLE:
            raise InvalidTimerTransition(
                f"Cannot start the timer from state {self._state.value!r}."
            )
        now = self._clock()
        self._session_start = now
        self._page_started_at = now
        self._state = TimerState.RUNNING

    def pause(self) -> None:
        """Pause the timer. Only valid from ``RUNNING``."""
        if self._state is not TimerState.RUNNING:
            raise InvalidTimerTransition(
                f"Cannot pause the timer from state {self._state.value!r}."
            )
        now = self._clock()
        assert self._page_started_at is not None
        elapsed = now - self._page_started_at
        self._actual_reading_seconds += elapsed
        self._page_accumulated_seconds += elapsed
        self._page_started_at = None
        self._pause_started_at = now
        self._state = TimerState.PAUSED

    def resume(self) -> None:
        """Resume the timer. Only valid from ``PAUSED``."""
        if self._state is not TimerState.PAUSED:
            raise InvalidTimerTransition(
                f"Cannot resume the timer from state {self._state.value!r}."
            )
        now = self._clock()
        assert self._pause_started_at is not None
        self._paused_seconds += now - self._pause_started_at
        self._pause_started_at = None
        self._page_started_at = now
        self._state = TimerState.RUNNING

    def finish_page(self) -> None:
        """Mark the current page as finished and reset the page timer.

        Only valid while ``RUNNING``: a page cannot be finished while the
        timer is paused.
        """
        if self._state is not TimerState.RUNNING:
            raise InvalidTimerTransition(
                "Cannot finish a page unless the timer is running "
                f"(current state: {self._state.value!r})."
            )
        now = self._clock()
        assert self._page_started_at is not None
        duration = self._page_accumulated_seconds + (now - self._page_started_at)
        self._actual_reading_seconds += now - self._page_started_at
        self._page_records.append(
            PageRecord(page_number=self._page_number, duration_seconds=duration)
        )
        self._page_number += 1
        self._page_started_at = now
        self._page_accumulated_seconds = 0.0

    def stop(self) -> TimerStats:
        """Stop the timer and return the final statistics.

        Valid from ``RUNNING`` or ``PAUSED`` ("any time" once started).
        """
        if self._state not in (TimerState.RUNNING, TimerState.PAUSED):
            raise InvalidTimerTransition(
                f"Cannot stop the timer from state {self._state.value!r}."
            )
        now = self._clock()
        if self._state is TimerState.RUNNING:
            assert self._page_started_at is not None
            elapsed = now - self._page_started_at
            self._actual_reading_seconds += elapsed
            duration = self._page_accumulated_seconds + elapsed
        else:
            assert self._pause_started_at is not None
            self._paused_seconds += now - self._pause_started_at
            duration = self._page_accumulated_seconds

        if duration > 0:
            # The page being read when the timer stopped was never finished
            # explicitly via ``finish_page``, but some time was spent on
            # it, so it still counts as read.
            self._page_records.append(
                PageRecord(page_number=self._page_number, duration_seconds=duration)
            )

        self._session_end = now
        self._state = TimerState.STOPPED
        return self._build_stats()

    def _build_stats(self) -> TimerStats:
        assert self._session_start is not None
        assert self._session_end is not None

        slowest = max(
            self._page_records, key=lambda r: r.duration_seconds, default=None
        )
        fastest = min(
            self._page_records, key=lambda r: r.duration_seconds, default=None
        )

        return TimerStats(
            pages_read=len(self._page_records),
            slowest_page=slowest,
            fastest_page=fastest,
            actual_reading_seconds=self._actual_reading_seconds,
            elapsed_seconds=self._session_end - self._session_start,
            paused_seconds=self._paused_seconds,
        )
