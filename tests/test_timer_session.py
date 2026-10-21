"""Tests for the interactive reading session key-handling loop."""

import re
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


_ANSI_SEQUENCE = re.compile(r"\x1b\[(\d*)([A-Za-z])")


def _replay_rows(raw: str) -> list[str]:
    """Replay raw terminal output (cursor-up and clear-line escapes, ``\\r``
    and ``\\n``) against a virtual screen buffer and return its rows.

    This mirrors how a real terminal would interpret the escape sequences
    emitted by ``_default_render``/``_clear_rendered_block``, so tests can
    assert the actual on-screen position of content instead of merely
    checking that *some* escape sequence was printed.
    """
    rows: list[str] = [""]
    row = col = 0
    i, n = 0, len(raw)

    def ensure(r: int) -> None:
        while len(rows) <= r:
            rows.append("")

    while i < n:
        char = raw[i]
        if char == "\x1b":
            match = _ANSI_SEQUENCE.match(raw, i)
            assert match is not None, f"unrecognized escape at {i!r}"
            count = int(match.group(1)) if match.group(1) else 1
            command = match.group(2)
            if command == "A":
                row = max(0, row - count)
            elif command == "K":
                ensure(row)
                rows[row] = rows[row][:col]
            i = match.end()
            continue
        if char == "\r":
            col = 0
        elif char == "\n":
            row += 1
            col = 0
            ensure(row)
        else:
            ensure(row)
            line = rows[row]
            if col < len(line):
                line = line[:col] + char + line[col + 1 :]
            else:
                line = line + " " * (col - len(line)) + char
            rows[row] = line
            col += 1
        i += 1
    return rows


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


def test_format_live_status_includes_book_title_and_author():
    timer = ReadingTimer(clock=make_clock())
    status = format_live_status(
        timer, book_title="Dune", book_author="Frank Herbert", width=40
    )
    assert "Dune" in status
    assert "Frank Herbert" in status
    assert "New reading session for 'Dune', by Frank Herbert" in status.replace(
        "\n", ""
    )


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


def test_echo_locked_clears_previous_block_before_scrolling_message(capsys):
    # Regression test for the header duplicating down the screen every
    # time a page finished: before this fix, ``_echo_locked`` printed the
    # scrolling message without erasing the previously rendered live
    # block first, so the block (including the "New reading session
    # for..." title) stayed on screen and a new one was rendered below it
    # on every tick, stacking up down the page.
    timer = ReadingTimer(clock=make_clock())
    rendered: list[str] = []
    session = ReadingSession(
        read_key=keys_from_sequence([]),
        timer=timer,
        echo=lambda msg: rendered.append(("echo", msg)),
        live_display=True,
        render_live_status=lambda status: rendered.append(("render", status)),
    )

    # Simulate a live block already having been rendered on a previous
    # tick, as the ticker thread would do.
    session._rendered_line_count = 3

    session._echo_locked("Page 1 finished. Reading page 2.")

    out = capsys.readouterr().out
    # The previous block must be erased (cursor moved up and each of its
    # lines cleared) before the scrolling message is printed.
    assert "\x1b[3A" in out
    assert "\x1b[K" in out
    assert rendered[0] == ("echo", "Page 1 finished. Reading page 2.")
    # The block is redrawn right after the message instead of leaving a
    # stale/duplicated block behind.
    assert rendered[1][0] == "render"


def test_live_block_home_row_is_stable_across_page_turns(capsys):
    # Regression test for the title duplicating down the screen on every
    # page turn (reported against three prior "fixed" attempts). Drives a
    # real ``ReadingSession`` with the *actual* ``_default_render``, then
    # replays the raw escape-sequence output against a virtual terminal
    # buffer, like a real terminal would. The title line must stay at the
    # same screen row across repeated echo/render cycles instead of
    # drifting or being duplicated further down the page.
    timer = ReadingTimer(clock=make_clock())
    session = ReadingSession(
        read_key=keys_from_sequence([]),
        timer=timer,
        echo=print,
        live_display=True,
        book_title="Dune",
        book_author="Frank Herbert",
    )

    session._render_live_status(
        format_live_status(timer, book_title="Dune", book_author="Frank Herbert")
    )
    for i in range(3):
        session._echo_locked(f"Page {i + 1} finished. Reading page {i + 2}.")

    raw = capsys.readouterr().out
    rows = _replay_rows(raw)

    title_rows = [
        idx for idx, line in enumerate(rows) if "New reading session" in line
    ]
    # The title must occupy exactly one screen row at any time -- it must
    # not be left behind as a stale duplicate while a new block is drawn
    # further down the page.
    assert len(title_rows) == 1, (
        f"title appeared at rows {title_rows}, expected a single stable row"
    )


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
