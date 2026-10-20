"""Command line interface for read-habit."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from read_habit import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="read-habit",
        description="Track your reading habits from the command line.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the read-habit console script."""
    parser = build_parser()
    parser.parse_args(argv)
    print("read-habit: nothing to do yet. Try --help.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
