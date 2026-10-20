"""CLI commands for managing books."""

from __future__ import annotations

import click

from read_habit.book.repository import BookNotFoundError, BookRepository


def _format_book(book) -> str:
    parts = [f"#{book.id}", book.title]
    if book.author:
        parts.append(f"by {book.author}")
    if book.total_pages:
        parts.append(f"({book.total_pages} pages)")
    return " ".join(parts)


@click.group("book")
def book_group() -> None:
    """Manage books that reading sessions can be linked to."""


@book_group.command("add")
@click.argument("title")
@click.option("--author", default=None, help="Author of the book.")
@click.option("--pages", "total_pages", type=int, default=None, help="Total number of pages.")
def add_command(title: str, author: str | None, total_pages: int | None) -> None:
    """Add a new book."""
    repo = BookRepository()
    book = repo.add(title=title, author=author, total_pages=total_pages)
    click.echo(f"Added {_format_book(book)}")


@book_group.command("list")
def list_command() -> None:
    """List all books."""
    repo = BookRepository()
    books = repo.list()
    if not books:
        click.echo("No books yet. Add one with 'read-habit book add <title>'.")
        return
    for book in books:
        click.echo(_format_book(book))


@book_group.command("update")
@click.argument("book_id", type=int)
@click.option("--title", default=None, help="New title.")
@click.option("--author", default=None, help="New author.")
@click.option("--pages", "total_pages", type=int, default=None, help="New total number of pages.")
def update_command(book_id: int, title: str | None, author: str | None, total_pages: int | None) -> None:
    """Update an existing book."""
    repo = BookRepository()
    try:
        book = repo.update(book_id, title=title, author=author, total_pages=total_pages)
    except BookNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Updated {_format_book(book)}")


@book_group.command("delete")
@click.argument("book_id", type=int)
def delete_command(book_id: int) -> None:
    """Delete a book."""
    repo = BookRepository()
    try:
        repo.delete(book_id)
    except BookNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Deleted book #{book_id}")
