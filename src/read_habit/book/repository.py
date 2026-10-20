"""JSON-backed persistence for :class:`Book` entities."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from read_habit.book.models import Book

DEFAULT_BOOKS_PATH = Path.home() / ".read-habit" / "books.json"

_BOOKS_ADAPTER = TypeAdapter(list[Book])


class BookNotFoundError(Exception):
    """Raised when a book with a given id does not exist."""


class BookRepository:
    """Stores books as a JSON array of objects in a single file.

    Parameters
    ----------
    path:
        Location of the JSON file. Defaults to ``~/.read-habit/books.json``.
        The file (and any missing parent directories) is created lazily
        on the first write.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else DEFAULT_BOOKS_PATH

    @property
    def path(self) -> Path:
        """Return the path backing this repository."""
        return self._path

    def list(self) -> list[Book]:
        """Return all stored books, ordered by id."""
        return sorted(self._load(), key=lambda book: book.id)

    def get(self, book_id: int) -> Book:
        """Return the book with ``book_id``, raising if it doesn't exist."""
        for book in self._load():
            if book.id == book_id:
                return book
        raise BookNotFoundError(f"No book with id {book_id}.")

    def add(self, title: str, author: str | None = None, total_pages: int | None = None) -> Book:
        """Create and persist a new book, assigning it the next free id."""
        books = self._load()
        next_id = max((book.id for book in books), default=0) + 1
        book = Book(id=next_id, title=title, author=author, total_pages=total_pages)
        books.append(book)
        self._save(books)
        return book

    def update(
        self,
        book_id: int,
        title: str | None = None,
        author: str | None = None,
        total_pages: int | None = None,
    ) -> Book:
        """Update the fields of an existing book and persist the change.

        Only fields explicitly passed (non-``None``) are modified.
        """
        books = self._load()
        for index, book in enumerate(books):
            if book.id == book_id:
                updates = {
                    key: value
                    for key, value in {
                        "title": title,
                        "author": author,
                        "total_pages": total_pages,
                    }.items()
                    if value is not None
                }
                merged = {**book.model_dump(), **updates}
                updated = Book(**merged)
                books[index] = updated
                self._save(books)
                return updated
        raise BookNotFoundError(f"No book with id {book_id}.")

    def delete(self, book_id: int) -> None:
        """Remove the book with ``book_id``, raising if it doesn't exist."""
        books = self._load()
        remaining = [book for book in books if book.id != book_id]
        if len(remaining) == len(books):
            raise BookNotFoundError(f"No book with id {book_id}.")
        self._save(remaining)

    def _load(self) -> list[Book]:
        if not self._path.exists():
            return []
        content = self._path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        return _BOOKS_ADAPTER.validate_json(content)

    def _save(self, books: list[Book]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = _BOOKS_ADAPTER.dump_python(books, mode="json")
        self._path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
