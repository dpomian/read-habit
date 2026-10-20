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

from collections.abc import Callable, Iterable

from read_habit.timer.models import TimerStats
from read_habit.timer.state import InvalidTimerTransition, ReadingTimer, TimerState

ENTER_KEYS = frozenset({"\r", "\n"})
PAUSE_RESUME_KEY = "k"
FINISH_PAGE_KEY = " "


class ReadingSession:
    """Runs the interactive loop for a single reading timer session."""

    def __init__(
        self,
        read_key: Callable[[], str],
        timer: ReadingTimer | None = None,
        echo: Callable[[str], None] = print,
    ) -> None:
        self._read_key = read_key
        self._timer = timer if timer is not None else ReadingTimer()
        self._echo = echo

    def run(self) -> TimerStats:
        """Run the session until the timer is stopped and return stats."""
        self._echo("Press Enter to start the timer.")
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
