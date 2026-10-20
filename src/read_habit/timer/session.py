"""Interactive key-driven session that drives a :class:`ReadingTimer`.

Key bindings (as described in the feature request):

* ``Enter`` -- start the timer (while idle) or stop it (while running or
  paused).
* ``k``     -- pause the timer (while running) or resume it (while paused).
* ``Space`` -- mark the current page as finished (only while running).

The session loop reads one key at a time via an injectable ``read_key``
callable, so it can be driven by real terminal input (the default, using
``click.getchar``) or by a scripted sequence of keys in tests.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable

from read_habit.timer.formatting import format_seconds
from read_habit.timer.models import TimerStats
from read_habit.timer.state import InvalidTimerTransition, ReadingTimer, TimerState

ENTER_KEYS = frozenset({"\r", "\n"})
PAUSE_RESUME_KEY = "k"
FINISH_PAGE_KEY = " "

DEFAULT_TICK_SECONDS = 0.2


def format_live_status(timer: ReadingTimer) -> str:
    """Render the current elapsed/page/paused times as a single status line."""
    state = timer.state
    if state is TimerState.IDLE:
        return "Elapsed: 0m 0s | Page 1: 0m 0s | Paused: 0m 0s"
    label = " (paused)" if state is TimerState.PAUSED else ""
    return (
        f"Elapsed: {format_seconds(timer.live_elapsed_seconds())} | "
        f"Page {timer.current_page}: {format_seconds(timer.live_page_seconds())}{label} | "
        f"Paused: {format_seconds(timer.live_paused_seconds())}"
    )


class ReadingSession:
    """Runs the interactive loop for a single reading timer session."""

    def __init__(
        self,
        read_key: Callable[[], str],
        timer: ReadingTimer | None = None,
        echo: Callable[[str], None] = print,
        live_display: bool = False,
        tick_seconds: float = DEFAULT_TICK_SECONDS,
        render_live_status: Callable[[str], None] | None = None,
    ) -> None:
        self._read_key = read_key
        self._timer = timer if timer is not None else ReadingTimer()
        self._echo = echo
        self._live_display = live_display
        self._tick_seconds = tick_seconds
        self._render_live_status = render_live_status or self._default_render
        self._stop_ticking = threading.Event()
        self._ticker_thread: threading.Thread | None = None

    def run(self) -> TimerStats:
        """Run the session until the timer is stopped and return stats."""
        self._echo("Press Enter to start the timer.")
        self._start_ticker()
        try:
            while self._timer.state is TimerState.IDLE:
                key = self._read_key()
                if key in ENTER_KEYS:
                    self._timer.start()
                    self._echo("Timer started. Reading page 1.")

            while True:
                key = self._read_key()
                try:
                    stats = self._handle_key(key)
                except InvalidTimerTransition:
                    # Ignore keys that are not valid in the current state,
                    # e.g. Space while paused, or 'k' while idle/stopped.
                    continue
                if stats is not None:
                    return stats
        finally:
            self._stop_ticker()

    def _start_ticker(self) -> None:
        if not self._live_display:
            return
        self._stop_ticking.clear()
        self._ticker_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._ticker_thread.start()

    def _stop_ticker(self) -> None:
        if self._ticker_thread is None:
            return
        self._stop_ticking.set()
        self._ticker_thread.join(timeout=self._tick_seconds * 2)
        self._ticker_thread = None

    def _tick_loop(self) -> None:
        while not self._stop_ticking.is_set():
            self._render_live_status(format_live_status(self._timer))
            if self._timer.state is TimerState.STOPPED:
                break
            self._stop_ticking.wait(self._tick_seconds)

    def _default_render(self, status: str) -> None:
        self._echo(f"\r{status}")

    def _handle_key(self, key: str) -> TimerStats | None:
        if key in ENTER_KEYS:
            stats = self._timer.stop()
            self._echo("Timer stopped.")
            return stats
        if key == PAUSE_RESUME_KEY:
            if self._timer.state is TimerState.RUNNING:
                self._timer.pause()
                self._echo("Timer paused. Press 'k' to resume.")
            else:
                self._timer.resume()
                self._echo(f"Timer resumed. Reading page {self._timer.current_page}.")
            return None
        if key == FINISH_PAGE_KEY:
            finished_page = self._timer.current_page
            self._timer.finish_page()
            self._echo(
                f"Page {finished_page} finished. Reading page "
                f"{self._timer.current_page}."
            )
            return None
        raise InvalidTimerTransition(f"Unrecognized key: {key!r}")


def keys_from_sequence(keys: Iterable[str]) -> Callable[[], str]:
    """Build a ``read_key`` callable that yields keys from a fixed sequence.

    Useful for tests. Raises :class:`StopIteration` if more keys are
    requested than were provided.
    """
    iterator = iter(keys)

    def _read_key() -> str:
        return next(iterator)

    return _read_key
