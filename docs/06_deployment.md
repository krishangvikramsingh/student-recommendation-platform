# Deployment

Verified deployment: **local only**, one Python process on `127.0.0.1:8000`, SQLite file on disk. No public hosting was
set up, so no public URL exists.

## Requirements
Python 3.10 or newer (tested on 3.13). No third-party runtime packages. `pytest`, `pytest-cov`, `requests` and
`playwright` are only needed for verification (`pip install -r requirements.txt`).

## Configuration (environment variables)
| Variable | Default | Meaning |
|---|---|---|
| `SRP_HOST` / `SRP_PORT` | `127.0.0.1` / `8000` | Listen address |
| `SRP_DB_PATH` | `data/platform.db` | SQLite file (created on first run) |
| `SRP_SESSION_MINUTES` | `30` | Idle session timeout |
| `SRP_ADMIN_EMAIL` | `admin@platform.in` | Administrator created on first run |
| `SRP_ADMIN_PASSWORD` | *(empty)* | If empty, a random password is generated and printed once on first run |
| `SRP_DEMO_DATA` | `1` | Load the sample listings and events on first run |

Copy `.env.example` as a reference. The application does not read `.env` files itself; export the variables or use your
process manager. Never commit real credentials.

## First run
```
cd student-recommendation-platform
export PYTHONPATH=src
export SRP_ADMIN_PASSWORD='choose-a-strong-password'
python -m srp
```
Open http://127.0.0.1:8000/ . On first run the database is created and seeded with sample data (city Mumbai, college NMIMS
MPSTME with domain `nmims.edu.in`, 10 sample listings and 3 events that start 3–16 days from the day of first run). All of
this is **sample data**, not real businesses.

## Tests and smoke test
```
python -m pytest -v                                   # 96 tests
python -m pytest --cov=srp --cov-report=term-missing  # with coverage
SRP_ADMIN_PASSWORD='choose-a-strong-password' python scripts/smoke_check.py   # against the running server
python scripts/nfr_checks.py                          # load/timing checks (about 2 minutes, writes docs/evidence/nfr_results.json)
python scripts/ui_walkthrough.py                      # browser walkthrough and screenshots (needs playwright + chromium)
```
The smoke test registers `smoke.student@nmims.edu.in`; run it once per database, or delete the database first.

## Troubleshooting
* *Address already in use*: change `SRP_PORT` or stop the other process.
* *Lost the generated admin password*: delete `data/platform.db` (this erases all data) and start again with `SRP_ADMIN_PASSWORD` set.
* *Everyone was logged out after a restart*: sessions are held in memory by design.
* *`ModuleNotFoundError: srp`*: set `PYTHONPATH=src` or run from the project root with `python -m srp` after exporting it.

## Making it public (not done)
Put a TLS-terminating reverse proxy (nginx, Caddy) in front, run the process under a supervisor, back up `platform.db`, and
set a strong `SRP_ADMIN_PASSWORD`. The built-in HTTP server is for demonstration, not for the open internet.
