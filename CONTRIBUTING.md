# Contributing

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
make test lint typecheck
```

The runtime has no dependencies; keep it that way. New behaviour needs a test, and `make test`
must stay above the coverage floor set in `pyproject.toml`.
