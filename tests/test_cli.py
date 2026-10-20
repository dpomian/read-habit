"""Tests for the read-habit CLI."""

import pytest

from read_habit import __version__
from read_habit.cli import build_parser, main


def test_main_returns_zero(capsys):
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "read-habit" in captured.out


def test_version_flag(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--version"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out
