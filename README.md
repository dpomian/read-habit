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
uv run read-habit read
```

Optionally link the session to a book by id:

```bash
uv run read-habit read --book 1
```

Controls:

- `Enter` -- start the timer (while idle), or stop it (any time once started).
- `k` -- pause the timer while running, or resume it while paused.
- `Space` -- mark the current page as finished and reset the per-page timer
  (only while running).

The timer enforces these states: a page cannot be marked finished while
paused, and pausing/resuming is only possible when the timer is running or
paused respectively. While the timer is running or paused, a live,
centered status screen -- showing the book title (if any), the current
status (`READING`/`PAUSED`), the elapsed and actual reading time, the
control reminders, and the current page with its own elapsed time -- is
redrawn in place every second. When stopped, it prints pages read, slowest
page, fastest page, actual reading time, elapsed time, and time spent
paused. Every session is persisted as a JSON record at
`~/.read-habit/sessions.json`, including the id of the book it was linked
to (if any).

### Books

Manage books that reading sessions can be linked to. Books are persisted
as a JSON file at `~/.read-habit/books.json`.

```bash
uv run read-habit book add "Dune" --author "Frank Herbert" --pages 412
uv run read-habit book list
uv run read-habit book update 1 --pages 420
uv run read-habit book delete 1
uv run read-habit book sessions 1
```

`book sessions <id>` lists the reading sessions recorded for that book
(pages read and reading time for each).

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
│       ├── book/         # book entity, JSON persistence and CLI commands
│       │   ├── __init__.py
│       │   ├── models.py      # pydantic Book model
│       │   ├── repository.py  # JSON-backed CRUD repository
│       │   └── cli.py         # `book` command group
│       └── timer/        # reading timer state machine and session
│           ├── __init__.py
│           ├── state.py       # ReadingTimer finite state machine
│           ├── session.py     # interactive key-driven loop
│           ├── models.py      # pydantic data models
│           ├── formatting.py  # stats presentation
│           └── repository.py  # JSON-backed session persistence
└── tests/                # test suite
```

## License

See [LICENSE](LICENSE) (MIT).
