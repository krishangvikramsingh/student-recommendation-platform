# Student Recommendation Platform for New City Students

[![CI](https://github.com/krishangvikramsingh/student-recommendation-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/krishangvikramsingh/student-recommendation-platform/actions) ![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue) ![License](https://img.shields.io/badge/license-MIT-green)

Software Engineering mini project — Krishang Vikram Singh, Roll No. B106, Batch C1, B.Tech Computer Engineering,
NMIMS Mukesh Patel School of Technology Management & Engineering (Mumbai).

A web application that helps students who have moved to a new city find PGs/hostels, restaurants, stationery shops, sports
facilities and local events, using college-verified accounts, administrator-moderated ratings and reviews, filters, location
search, personalised recommendations and notifications. The requirements, UML and DFD design and test cases come from
Experiments 1–10 of the Software Engineering lab record.

**Status:** working and tested locally (96 automated tests passing, 92 % line coverage, live smoke test and browser
walkthrough recorded in `docs/evidence/`). It has **not** been hosted publicly and it does **not** use HTTPS; see
*Known limitations*.

## Quick start
```
cd student-recommendation-platform
pip install -r requirements.txt        # only needed for tests; the app itself has no dependencies
export PYTHONPATH=src
export SRP_ADMIN_PASSWORD='choose-a-strong-password'
python -m srp
```
Open http://127.0.0.1:8000/ . The first run creates `data/platform.db` and loads **sample data** (city Mumbai, college NMIMS
MPSTME with email domain `nmims.edu.in`, 10 sample listings, 3 sample events).
Sign in as the administrator with `admin@platform.in` and the password you exported. Register a student with any address
ending in `@nmims.edu.in`. The account stays unconfirmed until its email link is used (see *Login workflow*).

Run the tests: `python -m pytest -v`. Run the smoke test against a running server:
`SRP_ADMIN_PASSWORD=... python scripts/smoke_check.py`. Full instructions: `docs/06_deployment.md`.

## What it does
| Area | Implemented |
|---|---|
| Accounts | Registration with college-domain check (exact or sub-domain, case-insensitive), duplicate detection, scrypt-hashed passwords, login, logout, 5-failure / 15-minute lockout, suspended accounts refused, idle session timeout |
| Discovery | Search by category within a radius (default 5 km) sorted by distance, price/rating/distance filters, verified review counts, empty-result guidance, chronological events with type/date filters, personalised recommendations from saved preferences |
| Reviews | Integer 1–5 rating, mandatory comment, spam/profanity checks, one review per listing per student, moderation queue, approve/reject, student reports, reported reviews leave the average until resolved |
| Notifications | In-app notifications for new events, review outcomes, moderation outcomes and reports; read/unread; per-category opt-out |
| Administration | Review moderation, verify/suspend/reinstate students, add/update colleges, cities and listings, archive listings, audit log |
| Quality | SQLite persistence with constraints, role checks on the server, safe error messages, security headers, masked emails, responsive and keyboard-accessible UI |

## Layout
```
src/srp/            application (models, service rules, SQLite store, HTTP server, web UI in web/)
tests/              96 pytest tests (service, API, persistence)
scripts/            smoke_check.py, nfr_checks.py, ui_walkthrough.py, gen_test_report.py
docs/               requirements inventory, traceability, consistency analysis, NFR results, test report,
                    deployment notes, diagrams (with sources), evidence (logs, screenshots)
report/             project report (Word and PDF)
data/               SQLite database is created here (git-ignored)
```
The architecture is a small layered monolith: browser UI, HTTP/JSON interface (`server.py`), business rules (`service.py`),
and persistence (`store.py`). Working data is held in memory and every change is written through to SQLite.

## API summary
Public: `GET /health /colleges /cities /search /events /listings/{id}`, `POST /register /login`.
Signed in: `POST /logout`, `GET /me`, `PUT /me/preferences`, `GET /recommend`, `GET /notifications`,
`POST /notifications/{id}/read`, `PUT /me/notification-settings`, `POST /reviews`, `POST /reviews/{id}/report`.
Administrator: `GET /admin/reviews /admin/users /admin/audit`, `POST /reviews/{id}/validate`,
`POST /admin/users/{id}/verify|suspend|reinstate`, `POST /admin/cities /admin/colleges /admin/listings`,
`PUT|DELETE /admin/listings/{id}`. Send the token from `/login` as `Authorization: Bearer <token>`.

## Login workflow
1. **Register** with a college email. The account is created unconfirmed and a single-use link (valid 24 h) is emailed.
2. **Confirm** by opening the link. Logging in before that is refused, and a new link can be requested.
3. **Log in.** The session is an `HttpOnly`, `SameSite=Strict` cookie (`Secure` behind HTTPS) that page scripts cannot read.
   Idle timeout 30 min, absolute lifetime 12 h. Five wrong passwords lock the account for 15 minutes.
4. **Forgot password:** a single-use link (valid 1 h) is emailed. The reply is identical whether or not the address has an
   account. Using it signs out every device and unlocks the account.
5. **Change password** in Settings. It needs the current password and signs out other devices.

Protections: tokens stored only as SHA-256 hashes, per-IP and per-address rate limits (HTTP 429 with `Retry-After`),
CSRF defence for cookie sessions (custom header plus Origin check), constant-time-ish login for unknown accounts, emailed
links built from `SRP_BASE_URL` only (never from request headers), CSP / frame / referrer / permissions headers, HSTS
when served over HTTPS. API clients may still send `Authorization: Bearer <token>` from `/login`.

| Setting | Default | Purpose |
|---|---|---|
| `SRP_MAIL` | `console` | `smtp` to send real mail (needs `SRP_SMTP_HOST`, `SRP_SMTP_PORT`, `SRP_SMTP_USER`, `SRP_SMTP_PASSWORD`, `SRP_MAIL_FROM`) |
| `SRP_BASE_URL` | none | Public URL used in emailed links. Required when `SRP_HOST` is not loopback |
| `SRP_COOKIE_SECURE` | `auto` | `1` always sets `Secure`; `auto` follows `X-Forwarded-Proto` when `SRP_TRUST_PROXY=1` |
| `SRP_TRUST_PROXY` | `0` | Trust the proxy's `X-Forwarded-For` / `-Proto` |
| `SRP_SESSION_HOURS` | `12` | Absolute session lifetime |
| `SRP_REQUIRE_EMAIL_VERIFICATION` | `1` | Keep on in production |
| `SRP_DEV_LINKS` | `0` | Loopback only: return emailed links in API responses so a local install works without SMTP. Ignored on public binds |

## Known limitations
* **No built-in HTTPS.** Put a TLS proxy in front before any public use and set `SRP_BASE_URL`, `SRP_TRUST_PROXY=1` and
  `SRP_COOKIE_SECURE=1`.
* **Mail needs configuring for real use.** Confirmation and reset links are delivered through SMTP (`SRP_MAIL=smtp`). The
  default `console` mailer only prints them. College-ID verification is not built.
* Reviews are published after administrator approval, not within one minute (see C-01 in the consistency analysis).
* "Edit-flag" moderation, slot booking, menu/inventory updates and other Experiment 5 operations without user stories are
  not implemented.
* Notifications are in-app only. Locations are sample coordinates; there is no map or third-party data.
* Sessions and rate-limit counters are in memory (lost on restart; only hashed session tokens are held). One process; no replication, backup job or archival job.
* Availability (99.5 %) and long-term retention could not be verified locally. Portability and accessibility were checked in
  Chromium with an automated scanner only. Login bursts of 20 simultaneous requests exceeded the 1-second target.
  Details and numbers: `docs/04_nfr_verification.md`.
* The Experiment 3 use-case image and the official mini-project guideline were not available when this was built; the
  use-case diagram was redrawn from Experiments 1, 4 and 5 (`docs/03_consistency_analysis.md`, C-14, C-15).

## Demonstration guide
1. Start the server; show the home page and search PG/Hostel (distance-sorted, cost, rating, review count).
2. Search from far away coordinates to show the "expand the radius" message; apply price and rating filters.
3. Register `name@nmims.edu.in`; try `name@gmail.com` and `name@notnmims.edu.in` to show rejection (US2, defect D-1).
4. Open a listing, submit a review, show that the rating does not change yet.
5. Log in as the administrator, approve the review, return to search: the rating and review count have changed (TC-04).
6. Report a review, show the admin queue, notifications and the audit log.
7. Show the Events tab filters, preferences on "For you", and the failed-login lockout (5 wrong passwords).
8. Run `python -m pytest -v` and `scripts/smoke_check.py`; show `docs/evidence/` and the traceability matrix.

## Docker

```bash
SRP_ADMIN_PASSWORD='choose-a-strong-one' docker compose up --build
```

Data lives in the `srp-data` volume. Put it behind HTTPS and set `SRP_BASE_URL`, `SRP_TRUST_PROXY=1`
and SMTP settings for real use. `make test lint typecheck` runs the checks CI runs.
