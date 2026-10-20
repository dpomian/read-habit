"""Command line interface for read-habit."""

from __future__ import annotations

import click

from read_habit import __version__
from read_habit.timer.formatting import format_stats
from read_habit.timer.session import ReadingSession


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="read-habit")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Track your reading habits from the command line."""
    if ctx.invoked_subcommand is None:
        click.echo("read-habit: nothing to do yet. Try --help.")


@cli.command("timer")
def timer_command() -> None:
    """Run an interactive reading timer session.

    Controls:
      Enter  start the timer / stop it (works any time once started)
      k      pause while running, resume while paused
      Space  mark the current page as finished (only while running)
    """
    click.echo("Reading timer -- Enter: start/stop, k: pause/resume, Space: next page.")
    session = ReadingSession(read_key=click.getchar)
    stats = session.run()
    click.echo(format_stats(stats))


def main(argv: list[str] | None = None) -> int:
    """Entry point for the read-habit console script."""
    result = cli.main(args=argv, prog_name="read-habit", standalone_mode=False)
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
