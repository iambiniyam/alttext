# Contributing

1. Open an issue before a large change.
2. Run `pytest -q` and `ruff check .`.
3. Keep the model optional. Tests must pass without downloading weights.
4. Do not add telemetry or cloud calls to the default path.

For a new scanner, add a fixture and a test in `tests/`.
