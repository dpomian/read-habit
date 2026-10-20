# Architecture

## Overview

`read-habit` is a command line tool for tracking reading habits, built as a
`uv`-managed Python project using a `src/` layout. The CLI is implemented
with `click`, and data is modeled with `pydantic`.

## Main components

- **`src/read_habit/cli.py`** -- CLI entry point. Defines the `read-habit`
  `click` group and registers the `read` and `book` subcommands.
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
  daemon ticker thread periodically re-renders a multi-line, centered
  status block (via `format_live_status()`/`format_session_display()`)
  showing the book title, status (`READING`/`PAUSED`/`WAITING TO START`),
  elapsed/actual time, control reminders, and current page time. The
  default renderer writes directly to `sys.stdout` (bypassing
  `echo`/`print`, which would append a newline and break the overwrite),
  moving the cursor back up over the previously rendered block with
  `\x1b[{n}A` and clearing each line with `\x1b[K` before rewriting it, so
  each tick redraws the whole block in place. A lock shared between the
  ticker thread and the main thread's progress messages prevents the two
  from interleaving on screen. Before printing a scrolling progress
  message (e.g. "Page N finished..."), the session erases the
  previously rendered live block first and redraws it right after the
  message, so the block never lingers on screen and duplicates itself
  down the page.
- **`src/read_habit/timer/models.py`** -- `pydantic` models `PageRecord`
  (page number and duration) and `TimerStats` (session summary: pages
  read, slowest/fastest page, actual reading time, elapsed time, paused
  time).
- **`src/read_habit/timer/formatting.py`** -- `format_stats()` renders a
  `TimerStats` instance as a human-readable summary block printed when a
  session stops; `format_session_display()`/`center_block()` render and
  center the live, in-progress status block shown while the timer runs.
- **`src/read_habit/timer/repository.py`** -- `SessionRepository`, a
  JSON-file-backed store for `ReadingSessionRecord` entities, defaulting to
  `~/.read-habit/sessions.json` (overridable via the constructor). `add()`
  persists a `TimerStats` together with an optional `book_id`, assigning
  the next free id; `list()` returns all stored sessions sorted by id.
- **`src/read_habit/timer/models.py`** -- also defines
  `ReadingSessionRecord` (id, optional `book_id`, `TimerStats`), the
  persisted representation of a finished session.
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
  `list`, `update`, `delete` and `sessions` subcommands; `sessions`
  resolves the book via `BookRepository` and filters
  `SessionRepository.list()` by `book_id`.

## Data flow

1. The user runs `read-habit read` (optionally with `--book <id>`, which
   is validated against `BookRepository` up front), constructing a
   `ReadingSession` wrapping a `ReadingTimer`.
2. `ReadingSession.run()` loops: it reads a key, forwards it to the timer
   (`start`/`pause`/`resume`/`finish_page`/`stop`), and echoes progress
   messages. Invalid actions for the current state raise
   `InvalidTimerTransition` and are silently ignored.
3. On `stop()`, `ReadingTimer` returns a `TimerStats` instance, which
   `cli.py` passes to `format_stats()` and prints to the terminal, then
   persists via `SessionRepository.add(stats, book_id=...)` as a
   `ReadingSessionRecord`.
4. `read-habit book sessions <id>` reads all records via
   `SessionRepository.list()` and filters them by `book_id` to show the
   sessions linked to that book.

## Where features live

- Reading timer feature (state machine, interactive loop, stats,
  persistence): entirely under `src/read_habit/timer/`.
- Book management (model, JSON persistence, CLI commands, linking
  sessions to a book): entirely under `src/read_habit/book/`.
- CLI wiring and command definitions: `src/read_habit/cli.py`.
- Tests mirror this structure under `tests/` (`test_cli.py`,
  `test_timer_session.py`, `test_timer_state.py`, `test_timer_cli.py`,
  `test_timer_repository.py`, `test_book_cli.py`,
  `test_book_repository.py`).
