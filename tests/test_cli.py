"""Tests for the read-habit CLI."""

from click.testing import CliRunner

from read_habit import __version__
from read_habit.cli import cli, main


def test_main_returns_zero(capsys):
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "read-habit" in captured.out


def test_version_flag():
    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output
