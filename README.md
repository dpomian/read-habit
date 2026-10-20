# read-habit

A command line interface for tracking reading habits.

## Requirements

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) for package and project management

## Getting started

Sync the environment (creates a virtualenv and installs the project):

```bash
uv sync
```

Run the CLI:

```bash
uv run read-habit --help
```

### Reading timer

Start an interactive reading timer session:

```bash
uv run read-habit timer
```

Controls:

- `Enter` -- start the timer (while idle), or stop it (any time once started).
- `k` -- pause the timer while running, or resume it while paused.
- `Space` -- mark the current page as finished and reset the per-page timer
  (only while running).

The timer enforces these states: a page cannot be marked finished while
paused, and pausing/resuming is only possible when the timer is running or
paused respectively. When stopped, it prints pages read, slowest page,
fastest page, actual reading time, elapsed time, and time spent paused.

You can also run the package directly as a module:

```bash
uv run python -m read_habit
```

## Development

Run the test suite:

```bash
uv run pytest
```

## Project layout

```
read-habit/
├── pyproject.toml        # project metadata and uv configuration
├── src/
│   └── read_habit/       # application package (src layout)
│       ├── __init__.py
│       ├── __main__.py   # enables `python -m read_habit`
│       ├── cli.py        # CLI entry point (click)
│       └── timer/        # reading timer state machine and session
│           ├── __init__.py
│           ├── state.py       # ReadingTimer finite state machine
│           ├── session.py     # interactive key-driven loop
│           ├── models.py      # pydantic data models
│           └── formatting.py  # stats presentation
└── tests/                # test suite
```

## License

See [LICENSE](LICENSE) (MIT).
