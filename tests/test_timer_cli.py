"""Tests for the `read` CLI command, in particular book association (#11)."""

from click.testing import CliRunner

import read_habit.cli as cli_module
from read_habit.cli import cli
from read_habit.timer.models import PageRecord, TimerStats


class _FakeSession:
    """Stand-in for ReadingSession that returns canned stats immediately."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def run(self) -> TimerStats:
        page = PageRecord(page_number=1, duration_seconds=5)
        return TimerStats(
            pages_read=1,
            slowest_page=page,
            fastest_page=page,
            actual_reading_seconds=5,
            elapsed_seconds=5,
            paused_seconds=0,
        )


def _invoke(args, books_path, sessions_path, monkeypatch):
    monkeypatch.setattr("read_habit.book.repository.DEFAULT_BOOKS_PATH", books_path)
    monkeypatch.setattr("read_habit.timer.repository.DEFAULT_SESSIONS_PATH", sessions_path)
    monkeypatch.setattr(cli_module, "ReadingSession", _FakeSession)
    return CliRunner().invoke(cli, args)


def test_timer_without_book_persists_session_with_no_book_id(tmp_path, monkeypatch):
    books_path = tmp_path / "books.json"
    sessions_path = tmp_path / "sessions.json"

    result = _invoke(["read"], books_path, sessions_path, monkeypatch)

    assert result.exit_code == 0
    from read_habit.timer.repository import SessionRepository

    sessions = SessionRepository(path=sessions_path).list()
    assert len(sessions) == 1
    assert sessions[0].book_id is None


def test_timer_with_valid_book_associates_session(tmp_path, monkeypatch):
    books_path = tmp_path / "books.json"
    sessions_path = tmp_path / "sessions.json"

    from read_habit.book.repository import BookRepository
    from read_habit.timer.repository import SessionRepository

    book = BookRepository(path=books_path).add(title="Dune")

    result = _invoke(["read", "--book", str(book.id)], books_path, sessions_path, monkeypatch)

    assert result.exit_code == 0

    sessions = SessionRepository(path=sessions_path).list()
    assert len(sessions) == 1
    assert sessions[0].book_id == book.id


def test_timer_with_unknown_book_fails_without_persisting(tmp_path, monkeypatch):
    books_path = tmp_path / "books.json"
    sessions_path = tmp_path / "sessions.json"

    result = _invoke(["read", "--book", "999"], books_path, sessions_path, monkeypatch)

    assert result.exit_code != 0
    assert "No book with id 999" in result.output

    from read_habit.timer.repository import SessionRepository

    assert SessionRepository(path=sessions_path).list() == []
