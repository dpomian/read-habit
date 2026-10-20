"""Command line interface for read-habit."""

from __future__ import annotations

import click

from read_habit import __version__
from read_habit.book.cli import book_group
from read_habit.book.repository import BookNotFoundError, BookRepository
from read_habit.timer.formatting import format_stats
from read_habit.timer.repository import SessionRepository
from read_habit.timer.session import ReadingSession


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="read-habit")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Track your reading habits from the command line."""
    if ctx.invoked_subcommand is None:
        click.echo("read-habit: nothing to do yet. Try --help.")


cli.add_command(book_group)


@cli.command("read")
@click.option(
    "--book",
    "book_id",
    type=int,
    default=None,
    help="Id of the book this reading session is for.",
)
def read_command(book_id: int | None) -> None:
    """Run an interactive reading timer session.

    Controls:
      Enter  start the timer / stop it (works any time once started)
      k      pause while running, resume while paused
      Space  mark the current page as finished (only while running)
    """
    book_title: str | None = None
    book_author: str | None = None
    if book_id is not None:
        try:
            book = BookRepository().get(book_id)
        except BookNotFoundError as exc:
            raise click.ClickException(str(exc)) from exc
        book_title = book.title
        book_author = book.author
        click.echo(f"Reading timer for '{book_title}'.")
    else:
        click.echo("Reading timer.")

    session = ReadingSession(
        read_key=click.getchar,
        live_display=True,
        book_title=book_title,
        book_author=book_author,
    )
    stats = session.run()
    click.echo(format_stats(stats))
    SessionRepository().add(stats, book_id=book_id)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the read-habit console script."""
    result = cli.main(args=argv, prog_name="read-habit", standalone_mode=False)
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
