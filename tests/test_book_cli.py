"""Tests for the book CLI commands."""

from click.testing import CliRunner

from read_habit.cli import cli


def _invoke(args, books_path, monkeypatch, sessions_path=None):
    monkeypatch.setattr("read_habit.book.repository.DEFAULT_BOOKS_PATH", books_path)
    if sessions_path is not None:
        monkeypatch.setattr("read_habit.timer.repository.DEFAULT_SESSIONS_PATH", sessions_path)
    return CliRunner().invoke(cli, args)


def test_list_empty(tmp_path, monkeypatch):
    result = _invoke(["book", "list"], tmp_path / "books.json", monkeypatch)
    assert result.exit_code == 0
    assert "No books yet" in result.output


def test_add_and_list(tmp_path, monkeypatch):
    books_path = tmp_path / "books.json"
    add_result = _invoke(
        ["book", "add", "Dune", "--author", "Frank Herbert", "--pages", "412"],
        books_path,
        monkeypatch,
    )
    assert add_result.exit_code == 0
    assert "Dune" in add_result.output

    list_result = _invoke(["book", "list"], books_path, monkeypatch)
    assert list_result.exit_code == 0
    assert "Dune" in list_result.output
    assert "Frank Herbert" in list_result.output
    assert "412 pages" in list_result.output


def test_update(tmp_path, monkeypatch):
    books_path = tmp_path / "books.json"
    _invoke(["book", "add", "Dune"], books_path, monkeypatch)

    result = _invoke(["book", "update", "1", "--pages", "412"], books_path, monkeypatch)
    assert result.exit_code == 0
    assert "412 pages" in result.output


def test_update_missing_book_fails(tmp_path, monkeypatch):
    result = _invoke(["book", "update", "999", "--title", "X"], tmp_path / "books.json", monkeypatch)
    assert result.exit_code != 0
    assert "No book with id 999" in result.output


def test_add_empty_title_fails(tmp_path, monkeypatch):
    result = _invoke(["book", "add", ""], tmp_path / "books.json", monkeypatch)
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "title" in result.output


def test_add_non_positive_pages_fails(tmp_path, monkeypatch):
    result = _invoke(["book", "add", "Dune", "--pages", "0"], tmp_path / "books.json", monkeypatch)
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "total_pages" in result.output


def test_update_empty_title_fails(tmp_path, monkeypatch):
    books_path = tmp_path / "books.json"
    _invoke(["book", "add", "Dune"], books_path, monkeypatch)

    result = _invoke(["book", "update", "1", "--title", ""], books_path, monkeypatch)
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "title" in result.output


def test_update_non_positive_pages_fails(tmp_path, monkeypatch):
    books_path = tmp_path / "books.json"
    _invoke(["book", "add", "Dune"], books_path, monkeypatch)

    result = _invoke(["book", "update", "1", "--pages", "-5"], books_path, monkeypatch)
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "total_pages" in result.output


def test_add_whitespace_only_title_fails(tmp_path, monkeypatch):
    result = _invoke(["book", "add", "   "], tmp_path / "books.json", monkeypatch)
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "title" in result.output


def test_add_strips_title_whitespace(tmp_path, monkeypatch):
    books_path = tmp_path / "books.json"
    add_result = _invoke(["book", "add", "  Dune  "], books_path, monkeypatch)
    assert add_result.exit_code == 0

    list_result = _invoke(["book", "list"], books_path, monkeypatch)
    assert "Dune" in list_result.output
    assert "  Dune  " not in list_result.output


def test_delete(tmp_path, monkeypatch):
    books_path = tmp_path / "books.json"
    _invoke(["book", "add", "Dune"], books_path, monkeypatch)

    result = _invoke(["book", "delete", "1"], books_path, monkeypatch)
    assert result.exit_code == 0
    assert "Deleted book #1" in result.output

    list_result = _invoke(["book", "list"], books_path, monkeypatch)
    assert "No books yet" in list_result.output


def test_delete_missing_book_fails(tmp_path, monkeypatch):
    result = _invoke(["book", "delete", "999"], tmp_path / "books.json", monkeypatch)
    assert result.exit_code != 0
    assert "No book with id 999" in result.output


def test_sessions_for_unknown_book_fails(tmp_path, monkeypatch):
    result = _invoke(["book", "sessions", "999"], tmp_path / "books.json", monkeypatch)
    assert result.exit_code != 0
    assert "No book with id 999" in result.output


def test_sessions_empty_for_existing_book(tmp_path, monkeypatch):
    books_path = tmp_path / "books.json"
    sessions_path = tmp_path / "sessions.json"
    _invoke(["book", "add", "Dune"], books_path, monkeypatch, sessions_path)

    result = _invoke(["book", "sessions", "1"], books_path, monkeypatch, sessions_path)
    assert result.exit_code == 0
    assert "No reading sessions recorded for 'Dune'" in result.output


def test_sessions_lists_only_sessions_for_that_book(tmp_path, monkeypatch):
    books_path = tmp_path / "books.json"
    sessions_path = tmp_path / "sessions.json"
    _invoke(["book", "add", "Dune"], books_path, monkeypatch, sessions_path)

    from read_habit.timer.models import PageRecord, TimerStats
    from read_habit.timer.repository import SessionRepository

    page = PageRecord(page_number=1, duration_seconds=5)
    stats = TimerStats(
        pages_read=1,
        slowest_page=page,
        fastest_page=page,
        actual_reading_seconds=5,
        elapsed_seconds=5,
        paused_seconds=0,
    )
    session_repo = SessionRepository(path=sessions_path)
    session_repo.add(stats, book_id=1)
    session_repo.add(stats, book_id=None)

    result = _invoke(["book", "sessions", "1"], books_path, monkeypatch, sessions_path)
    assert result.exit_code == 0
    assert "#1" in result.output
    assert "1 pages" in result.output
