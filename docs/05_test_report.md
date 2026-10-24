# Test report

Command (from the project root): `python -m pytest -v --cov=srp --cov-report=term-missing`
Result recorded in `evidence/pytest_output.txt`: **96 passed, 0 failed**, line coverage of `src/srp` **92 %** (`__main__.py`,
the start-up wrapper, is covered only by the manual deployment run).
Every one of the 96 tests with its result is listed in `test_results_generated.md` (generated from `evidence/junit.xml`).

| File | Tests | Purpose |
|---|---|---|
| `tests/test_case_study.py` | 4 | The four core test cases from Experiment 9 (unchanged except import paths) |
| `tests/test_extended.py` | 22 | Extended tests from Experiment 9/10 (unchanged except import paths) |
| `tests/test_features.py` | 42 | Admin management, authorisation, notifications, events, moderation, validation, hashing |
| `tests/test_api.py` | 22 | HTTP API on a live server: status codes, sessions, confidentiality, headers, malformed input |
| `tests/test_persistence.py` | 6 | SQLite persistence across restarts, constraints |

## Core test cases (Experiment 9)
| ID | Test function | Objective | Input | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| TC-01 | `test_tc01_registration_rejects_non_college_email` | Reject registration with a non-college email | `rahul@gmail.com`, college NMIMS | `InvalidCollegeEmail`; no account created | As expected | PASS |
| TC-02 | `test_tc02_account_locks_after_five_failed_logins` | Lock after 5 failed logins | 5 wrong passwords, then the right one | 6th attempt raises `AccountLocked` | As expected | PASS |
| TC-03 | `test_tc03_unverified_student_cannot_submit_review` | Unverified student cannot review | rating 4 from an unverified user | `NotVerified`; no review stored | As expected | PASS |
| TC-04 | `test_tc04_validated_reviews_update_rating_shown_in_search` | Approved reviews change the search rating | ratings 4 and 5, both approved | search shows 4.5 | As expected | PASS |

## Historical defects (Experiment 10) — regression tests
| ID | Test function | Input | Expected | Result |
|---|---|---|---|---|
| D-1 | `test_lookalike_domain_is_rejected` | `fake@notnmims.edu.in` | `InvalidCollegeEmail` | PASS |
| D-2 | `test_duplicate_email_check_ignores_case` | `ASHA@nmims.edu.in` after `asha@nmims.edu.in` | `DuplicateAccount` | PASS |
| D-3 | `test_suspended_account_cannot_login` | correct password for a suspended student | login refused | PASS |
| D-4 | `test_fractional_rating_is_rejected` | rating 4.5 | `InvalidReview` | PASS |
| D-4b | `test_boolean_rating_is_rejected` | rating `True` | `InvalidReview` | PASS |

## Other categories covered
Valid registration and login, invalid credentials, lock expiry after 16 minutes (fake clock), search sorting, radius
boundary, empty results, price and rating filters, combined filters, review approval and rejection, reported reviews and
average recalculation, notification routing and opt-out, authorisation failures for every administrator operation, input
validation (coordinates, price level, category, event date, details keys), API error responses (400/401/403/404/409/422/423),
oversized and malformed bodies, path traversal, security headers, and persistence of accounts, lock state, reviews,
reports, notifications and the audit log.

## Other verification runs (not pytest)
| Script | Evidence | Outcome |
|---|---|---|
| `scripts/smoke_check.py` against the running server | `evidence/smoke_output.txt` | 18 checks, all PASS |
| Restart of the deployed server | `evidence/restart_persistence.txt` | accounts, lock state, review and rating survived |
| `scripts/nfr_checks.py` | `evidence/nfr_results.json` | see `04_nfr_verification.md` |
| `scripts/ui_walkthrough.py` | `evidence/ui_walkthrough.json`, `evidence/screens/` | register, search, review, moderation and recommendation flow completed in Chromium; 3 clicks; no axe violations on 7 screens |

## History
The first prototype (Exp 9) failed 4 of 26 tests; the fixes of Exp 10 made all 26 pass. Both real runs are preserved in
`evidence/history/`. No test was weakened or removed afterwards.
