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
│       └── cli.py        # CLI entry point
└── tests/                # test suite
```

## License

See [LICENSE](LICENSE) (MIT).
