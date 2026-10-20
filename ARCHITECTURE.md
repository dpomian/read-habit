# Architecture

## Overview

`read-habit` is a command line tool for tracking reading habits, built as a
`uv`-managed Python project using a `src/` layout. The CLI is implemented
with `click`, and data is modeled with `pydantic`.

## Main components

- **`src/read_habit/cli.py`** -- CLI entry point. Defines the `read-habit`
  `click` group and registers the `timer` and `book` subcommands.
  `main()` is the console script entry point registered in
  `pyproject.toml`.
- **`src/read_habit/timer/state.py`** -- `ReadingTimer`, a finite state
  machine with states `IDLE`, `RUNNING`, `PAUSED`, `STOPPED`. It enforces
  valid transitions (e.g. a page can only be finished while `RUNNING`,
  pause/resume only toggle between `RUNNING`/`PAUSED`) and raises
  `InvalidTimerTransition` otherwise. It tracks per-page durations and
  accumulates actual reading time, elapsed time, and paused time, using an
  injectable clock for deterministic testing.
- **`src/read_habit/timer/session.py`** -- `ReadingSession` drives the
  interactive key-driven loop on top of a `ReadingTimer`: it reads one key
  at a time via an injectable `read_key` callable (`click.getchar` by
  default), maps `Enter`/`k`/`Space` to timer actions, and ignores keys
  that are invalid in the current state. When `live_display=True`, a
  daemon ticker thread periodically renders the elapsed/per-page/paused
  status in place: the default renderer writes directly to `sys.stdout`
  (bypassing `echo`/`print`, which would append a newline and break the
  overwrite) with a `\r<status>\x1b[K` sequence that returns to the start
  of the line and clears it before printing the new status, so each tick
  overwrites the previous one in place. A lock shared between the ticker
  thread and the main thread's progress messages prevents the two from
  interleaving on screen.
- **`src/read_habit/timer/models.py`** -- `pydantic` models `PageRecord`
  (page number and duration) and `TimerStats` (session summary: pages
  read, slowest/fastest page, actual reading time, elapsed time, paused
  time).
- **`src/read_habit/timer/formatting.py`** -- `format_stats()` renders a
  `TimerStats` instance as a human-readable summary block printed when a
  session stops.
- **`src/read_habit/book/models.py`** -- `pydantic` model `Book` (id,
  title, optional author, optional total pages) representing a book that
  reading sessions can be linked to.
- **`src/read_habit/book/repository.py`** -- `BookRepository`, a
  JSON-file-backed CRUD store for `Book` entities, defaulting to
  `~/.read-habit/books.json` (overridable via the constructor). Loads and
  dumps the whole list through a `pydantic` `TypeAdapter`, assigns the
  next free id on `add()`, and raises `BookNotFoundError` from `get()`,
  `update()` and `delete()` when the id doesn't exist.
- **`src/read_habit/book/cli.py`** -- `book` `click` group with `add`,
  `list`, `update` and `delete` subcommands, each operating on a
  `BookRepository` instance.

## Data flow

1. The user runs `read-habit timer`, which constructs a `ReadingSession`
   wrapping a `ReadingTimer`.
2. `ReadingSession.run()` loops: it reads a key, forwards it to the timer
   (`start`/`pause`/`resume`/`finish_page`/`stop`), and echoes progress
   messages. Invalid actions for the current state raise
   `InvalidTimerTransition` and are silently ignored.
3. On `stop()`, `ReadingTimer` returns a `TimerStats` instance, which
   `cli.py` passes to `format_stats()` and prints to the terminal.

## Where features live

- Reading timer feature (state machine, interactive loop, stats): entirely
  under `src/read_habit/timer/`.
- Book management (model, JSON persistence, CLI commands): entirely under
  `src/read_habit/book/`.
- CLI wiring and command definitions: `src/read_habit/cli.py`.
- Tests mirror this structure under `tests/` (`test_cli.py`,
  `test_timer_session.py`, `test_timer_state.py`, `test_book_cli.py`,
  `test_book_repository.py`).
