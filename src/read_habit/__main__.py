"""Allow running the package with ``python -m read_habit``."""

from read_habit.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
