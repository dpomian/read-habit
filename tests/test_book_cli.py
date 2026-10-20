"""Tests for the book CLI commands."""

from click.testing import CliRunner

from read_habit.cli import cli


def _invoke(args, books_path, monkeypatch):
    monkeypatch.setattr("read_habit.book.repository.DEFAULT_BOOKS_PATH", books_path)
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
