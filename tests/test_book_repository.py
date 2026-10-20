"""Tests for the JSON-backed book repository."""

import pytest

from read_habit.book.repository import BookNotFoundError, BookRepository


@pytest.fixture
def repo(tmp_path):
    return BookRepository(path=tmp_path / "books.json")


def test_list_is_empty_when_file_does_not_exist(repo):
    assert repo.list() == []


def test_add_assigns_incrementing_ids(repo):
    first = repo.add(title="Dune")
    second = repo.add(title="Foundation", author="Isaac Asimov", total_pages=255)

    assert first.id == 1
    assert second.id == 2
    assert second.author == "Isaac Asimov"
    assert second.total_pages == 255


def test_add_persists_across_repository_instances(tmp_path):
    path = tmp_path / "books.json"
    BookRepository(path=path).add(title="Dune")

    reloaded = BookRepository(path=path)
    books = reloaded.list()

    assert len(books) == 1
    assert books[0].title == "Dune"


def test_get_returns_matching_book(repo):
    added = repo.add(title="Dune")
    fetched = repo.get(added.id)
    assert fetched == added


def test_get_raises_when_missing(repo):
    with pytest.raises(BookNotFoundError):
        repo.get(999)


def test_update_changes_only_given_fields(repo):
    added = repo.add(title="Dune", author="Frank Herbert")
    updated = repo.update(added.id, total_pages=412)

    assert updated.title == "Dune"
    assert updated.author == "Frank Herbert"
    assert updated.total_pages == 412


def test_update_raises_when_missing(repo):
    with pytest.raises(BookNotFoundError):
        repo.update(999, title="New title")


def test_delete_removes_book(repo):
    added = repo.add(title="Dune")
    repo.delete(added.id)
    assert repo.list() == []


def test_delete_raises_when_missing(repo):
    with pytest.raises(BookNotFoundError):
        repo.delete(999)


def test_list_is_sorted_by_id(repo):
    repo.add(title="Second")
    repo.add(title="Third")
    repo.delete(1)
    repo.add(title="Fourth")

    ids = [book.id for book in repo.list()]
    assert ids == sorted(ids)
