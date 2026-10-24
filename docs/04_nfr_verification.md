# NFR verification

Every target below is the one written in Experiment 2. "Result" is what was actually measured by the scripts named in the
last column; raw output is in `evidence/`. **All measurements were taken on one 4-core cloud container with the client and
server on the same machine (loopback network), Python 3.13 and the standard-library HTTP server.** They show how this
implementation behaves in that environment only and do not prove production behaviour.

Dataset for the load checks: 100,001 users, 2,010 listings and 20,000 published
reviews loaded into a SQLite file (users share one precomputed password hash so that bulk loading is fast).

| Attribute | Target (Exp 2) | Implemented? | How tested | Measured result | Verdict | Limits |
|---|---|---|---|---|---|---|
| Performance, non-search | ≤ 1 s | Yes | 30 sequential requests each to login, listing detail, health | median login 0.0507 s, p95 0.0597 s, max 0.0637 s; listing detail median 0.0036 s | **Met** for single requests | Under 20 parallel logins the median was 1.0934 s (p95 1.6275 s, max 1.8956 s) because password hashing is deliberately slow (about 50 ms each) and runs one at a time inside the platform lock, so this burst **missed** the target |
| Performance, search | ≤ 3 s | Yes | 30 sequential searches over the large dataset | median 0.006 s, p95 0.0082 s, max 0.0097 s | **Met** | Events list and listing detail were not timed separately |
| Scalability | search ≤ 3 s with 100 000 users and 500 concurrent sessions | Partly | 500 users logged in (20 at a time) giving 500 live sessions, then 500 simultaneous searches | all 500 searches succeeded; median 1.3947 s, p95 1.8557 s, max 1.9368 s (wall time 3.82 s) | **Met** for search | The 500 sessions were real server sessions but the requests came from one client machine; login ramp of 500 users took 28.89 s in total. Everything runs in one process, so there is no horizontal scaling |
| Reliability | 99.9 % of review submissions recorded correctly | Yes | 500 simultaneous review submissions by 500 different users; counted HTTP 201 responses, objects in memory and rows in the database | 500/500 accepted, 500 in memory, 500 rows in the database, no duplicates; latency median 0.8324 s, max 0.9877 s | **Met** in this test | 500 attempts cannot demonstrate 99.9 % statistically (one failure would be 99.8 %); no failure injection was done |
| Recoverability | restore within 8 h after a simulated outage | Partly | Stopped the server and started it again on the same database file | healthy again after 2.06 s with 100,001 users and 20,500 reviews reloaded; the deployed demo also kept accounts, lock state, reviews and ratings (`evidence/restart_persistence.txt`) | **Met for a process restart only** | No backup, replication or disk-loss recovery procedure exists; sessions are held in memory and are lost on restart |
| Availability | 99.5 % monthly | No | – | not measured | **Not verified** | Requires long-running monitored hosting; none was set up |
| Security: authentication | authenticated sessions | Yes | API tests (401 without token, 403 for wrong role, logout and idle expiry, suspension revokes sessions) | all pass | **Met** | Tokens are random 192-bit values held in server memory |
| Security: encrypted transport | encrypted in transit | No | – | The server speaks plain HTTP on 127.0.0.1 | **Not met** | A TLS-terminating reverse proxy is required for any real deployment; not built or tested |
| Security: rate-limited and logged failures | yes | Yes | lockout tests, `test_lockout_is_recorded_in_audit_log` | 5 failures lock for 15 min; each failure written to the audit log | **Met** for per-account limiting | No per-IP limit; a single client can still try many different accounts |
| Passwords | (implied by "account security") | Yes | `test_passwords_are_salted_and_verifiable`, `test_stored_password_is_not_plaintext` | scrypt with a random salt (n=16384, r=8, p=1) | **Met** | – |
| Data retention | ≥ 2 years before archival | Partly | `test_archived_listing_leaves_search_but_keeps_reviews`, restart tests | no code path deletes reviews, reports or audit rows; listings are only archived | **Met by design** | Elapsed time cannot be tested; no archival job exists |
| Usability | register and search in ≤ 5 clicks | Yes | `scripts/ui_walkthrough.py` counts clicks in a real browser | 3 clicks (open Register, submit the form, press Search), because registration logs the user in automatically | **Met** | Walkthrough by the developer, not a user study |
| Data integrity | reject bad ratings, empty fields, spam/profanity | Yes | unit, API and database-constraint tests | all pass; the database also refuses ratings outside 1–5, duplicate emails and dangling foreign keys | **Met** | Spam and profanity detection is a short word list plus URL and repeated-character rules |
| Confidentiality | no private contact or verification detail exposed | Yes | `test_public_responses_never_expose_private_details`, `test_admin_user_list_masks_email` | public responses carry display name and review text only; admin list shows masked email | **Met** | Administrators see masked emails; the logged-in user sees their own email through `/me` |
| Portability | Chrome, Edge, Safari; Android and iOS sizes | Partly | Chromium (desktop 1180 px, phone 390 px) via Playwright | core flows work in Chromium; phone width has no horizontal scroll (no overflow) | **Partly met** | Edge, Safari, Firefox and real devices were not tested |
| Accessibility | WCAG 2.1 AA | Partly | axe-core 4.x (WCAG 2 A/AA, 2.1 A/AA tags) on 7 screens | 0 violations, 150 rules passed in total across the screens | **Partly met** | Automated scans find only a fraction of issues; no manual screen-reader or keyboard-only audit was done (forms use labels and visible focus outlines) |
| Stability / audit logging | log account and verification changes | Yes | audit tests | register, verify, suspend, reinstate, moderation and catalogue edits are logged with actor, time and target | **Met** | – |

## Findings worth knowing
1. **Login bursts are slower than the 1 s target.** Hashing takes about 50 ms and runs under a single lock. A burst of 20 simultaneous
   logins queued behind each other. Moving verification outside the lock would help, but it would also let parallel
   guesses slip past the lockout counter, so the lock was kept. More worker processes or a faster server would be the
   production answer.
2. **Search was slow until it was profiled.** The first run took a median of 19 s for 500 simultaneous searches because every
   result recounted all published reviews. Counting once per request and limiting results to 50 reduced this to the
   figures above. The 20 000-review dataset and the full test suite were re-run after the change.
3. Environment limits: shared container, single client machine, no network latency, no TLS cost.
