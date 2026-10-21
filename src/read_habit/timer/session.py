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

import sys
import threading
from collections.abc import Callable, Iterable

from read_habit.timer.formatting import format_session_display
from read_habit.timer.models import TimerStats
from read_habit.timer.state import InvalidTimerTransition, ReadingTimer, TimerState

ENTER_KEYS = frozenset({"\r", "\n"})
PAUSE_RESUME_KEY = "k"
FINISH_PAGE_KEY = " "

DEFAULT_TICK_SECONDS = 0.2


def format_live_status(
    timer: ReadingTimer,
    book_title: str | None = None,
    width: int | None = None,
    book_author: str | None = None,
) -> str:
    """Render the full live session display for the current timer state."""
    state = timer.state
    if state is TimerState.PAUSED:
        status_label = "PAUSED"
    elif state is TimerState.IDLE:
        status_label = "WAITING TO START"
    elif state is TimerState.STOPPED:
        status_label = "STOPPED"
    else:
        status_label = "READING"
    return format_session_display(
        book_title=book_title,
        status_label=status_label,
        elapsed_seconds=timer.live_elapsed_seconds(),
        actual_seconds=timer.live_actual_seconds(),
        current_page=timer.current_page,
        page_seconds=timer.live_page_seconds(),
        width=width,
        book_author=book_author,
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
        book_title: str | None = None,
        book_author: str | None = None,
    ) -> None:
        self._read_key = read_key
        self._timer = timer if timer is not None else ReadingTimer()
        self._echo = echo
        self._live_display = live_display
        self._tick_seconds = tick_seconds
        self._render_live_status = render_live_status or self._default_render
        self._book_title = book_title
        self._book_author = book_author
        self._stop_ticking = threading.Event()
        self._ticker_thread: threading.Thread | None = None
        self._output_lock = threading.Lock()
        self._rendered_line_count = 0

    def run(self) -> TimerStats:
        """Run the session until the timer is stopped and return stats."""
        self._echo("Press Enter to start the timer.")
        self._start_ticker()
        try:
            while self._timer.state is TimerState.IDLE:
                key = self._read_key()
                if key in ENTER_KEYS:
                    self._timer.start()
                    self._echo_locked("Timer started. Reading page 1.")

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
            with self._output_lock:
                self._render_live_status(
                    format_live_status(
                        self._timer,
                        book_title=self._book_title,
                        book_author=self._book_author,
                    )
                )
            if self._timer.state is TimerState.STOPPED:
                break
            self._stop_ticking.wait(self._tick_seconds)

    def _default_render(self, status: str) -> None:
        # Write directly to stdout (not through ``self._echo``/``print``)
        # so the block can be overwritten in place on every tick instead
        # of scrolling new lines. Move the cursor back up to the start of
        # the previously rendered block (if any), then rewrite each line,
        # clearing it first so shorter lines don't leave stale characters.
        lines = status.split("\n")
        if self._rendered_line_count:
            sys.stdout.write(f"\x1b[{self._rendered_line_count}A")
        for line in lines:
            sys.stdout.write(f"\r{line}\x1b[K\n")
        self._rendered_line_count = len(lines)
        sys.stdout.flush()

    def _clear_rendered_block(self) -> None:
        # Move the cursor back up to the start of the previously rendered
        # live block (if any) and blank out each of its lines, so the
        # block does not linger on screen as a stale, duplicate frame.
        #
        # ``_default_render`` ends each line with ``\n``, so after writing
        # ``N`` lines the cursor sits one row *below* the block, at
        # ``top + N``. To blank the block in place we move up ``N`` rows to
        # ``top``, then write ``N`` blank lines, which (because each of
        # those also ends with ``\n``) leaves the cursor back at
        # ``top + N`` -- i.e. directly below the now-blank block. That is
        # exactly where the next bit of output (a scrolling message, or a
        # fresh render of the block) belongs: moving up a second time here
        # would land back on the block's own first row and let a plain
        # ``print()`` overwrite the title instead of appending below it,
        # permanently shifting the block's home row up each time a message
        # is echoed.
        if not self._rendered_line_count:
            return
        sys.stdout.write(f"\x1b[{self._rendered_line_count}A")
        for _ in range(self._rendered_line_count):
            sys.stdout.write("\r\x1b[K\n")
        sys.stdout.flush()
        self._rendered_line_count = 0

    def _echo_locked(self, message: str) -> None:
        with self._output_lock:
            # Erase the previous live block before printing a normal
            # scrolling message, otherwise the block is left behind on
            # screen and a fresh block printed below it every tick ends
            # up duplicating the title/header down the page.
            self._clear_rendered_block()
            self._echo(message)
            if self._live_display:
                # Redraw the block immediately below the message instead
                # of waiting for the next tick, so there is no stale gap
                # and the next tick's cursor-up tracking starts in sync.
                self._render_live_status(
                    format_live_status(
                        self._timer,
                        book_title=self._book_title,
                        book_author=self._book_author,
                    )
                )

    def _handle_key(self, key: str) -> TimerStats | None:
        if key in ENTER_KEYS:
            stats = self._timer.stop()
            self._echo_locked("Timer stopped.")
            return stats
        if key == PAUSE_RESUME_KEY:
            if self._timer.state is TimerState.RUNNING:
                self._timer.pause()
                self._echo_locked("Timer paused. Press 'k' to resume.")
            else:
                self._timer.resume()
                self._echo_locked(f"Timer resumed. Reading page {self._timer.current_page}.")
            return None
        if key == FINISH_PAGE_KEY:
            finished_page = self._timer.current_page
            self._timer.finish_page()
            self._echo_locked(
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
