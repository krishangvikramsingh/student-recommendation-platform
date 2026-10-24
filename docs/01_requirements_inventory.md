# Requirements inventory

Sources studied for this build: Experiments 1, 2, 4 and 5 (the supplied `.docx` files), the Experiment 6–8 records
produced earlier in this project, the Experiment 9–10 records and their code, and the instruction text for the
mini-project. **Not available to this build:** `SE - Mini Project.docx` (the official guideline) and the Experiment 3
use-case image. The submission rules in the project brief (15-page report, software, tests, README, deployment notes) were
used in place of the guideline, and the use-case diagram was redrawn from Experiments 1, 4 and 5 (see
`03_consistency_analysis.md`, items C-14 and C-15).

Labels: **[D]** documented explicitly in an experiment, **[I]** inferred from the design, **[A]** an implementation
decision made during this build.

## Actors and permissions
| Actor | Source | Permissions |
|---|---|---|
| New student / Student | [D] Exp 1, 4, 5 | Register, log in, search, filter, view events, view details, receive recommendations and notifications |
| Verified student | [D] Exp 1 | All of the above plus submit and report reviews |
| Administrator | [D] Exp 1, 5 | Moderate reviews, manage students, colleges, cities, listings; view audit log |
| Anonymous visitor | [A] | Search, events and listing details are public so that the "5 clicks" usability target is reachable |

## Functional requirements (Experiment 1 user stories)
| ID | Requirement | Label |
|---|---|---|
| US1 | Register with college email and password; duplicate email rejected; confirmation shown | [D] |
| US2 | College verification; invalid or non-college email rejected and account stays unverified | [D] |
| US3 | Login within 3 s; error on bad credentials; 5 consecutive failures lock the account 15 minutes | [D] |
| US4 | Search by category within 5 km, sorted by distance; listing shows rating, cost, distance, verified review count; empty result prompts to expand radius | [D] |
| US5 | Events listed chronologically with date, location, category; category and date filters | [D] |
| US6 | Verified student submits 1–5 star review with comment; unverified blocked | [D] |
| US7 | Report a review with reason; status becomes "Under Review"; admin notified; no duplicate reports | [D] |
| US8 | Personalised recommendations from preferences and location; preference changes apply in the same session | [D] |
| US9 | Filter by price, rating, distance together; reset restores everything | [D] |
| US10 | Notifications for events and updates; read/unread persisted; per-category opt-out | [D] |
| US11 | Admin dashboard: approve/edit-flag/remove reviews, notify reporter, suspend/reinstate accounts with logging | [D] |
| BR-1 | Domain match must be exact or a subdomain of the registered college domain (look-alike domains rejected) | [D] Exp 10 |
| BR-2 | Email addresses are compared case-insensitively | [D] Exp 10 |
| BR-3 | Suspended accounts cannot log in | [D] Exp 10 |
| BR-4 | Ratings are integers 1–5; booleans and fractions rejected | [D] Exp 10 |
| BR-5 | Only published reviews contribute to the average rating | [D] Exp 9 (TC-04) |
| BR-6 | A review is published only after administrator approval | [I] Exp 4/5/9 (conflicts with US6 wording, see C-01) |
| BR-7 | Password minimum length 8, salted scrypt hashes | [A] |
| BR-8 | One non-rejected review per student per listing | [A] derived from the Exp 2 "no duplicate entries" story |
| BR-9 | Reported reviews are excluded from the average until the admin resolves them | [A] |
| BR-10 | Listings are archived (hidden), not deleted, so reviews are retained | [A] derived from the Exp 2 retention story |
| BR-11 | Event listings require a date; past events are hidden from search and the events list | [I] Exp 1 US5 and Exp 5 `Event.eventDate` |

## Non-functional requirements (Experiment 2)
Performance (1 s non-search, 3 s search), availability 99.5 %, security (authenticated, encrypted, rate-limited and
logged), data retention 2 years, usability (5 clicks), reliability 99.9 %, recoverability 8 h, data integrity (range,
mandatory fields, spam/profanity), scalability (100 000 users, 500 sessions, search < 3 s), confidentiality, portability
(Chrome, Edge, Safari, Android/iOS screen sizes), accessibility (WCAG 2.1 AA). System-wide constraints: account and
verification changes logged with user, time and action; reviews validated before publication. All **[D]**.
Results for each target are in `04_nfr_verification.md`.

## Design elements (Experiments 4–8)
Activities and swimlanes (Exp 4); twelve classes with attributes, operations and multiplicities (Exp 5); sequence
scenarios (Exp 6); collaboration messages (Exp 7); DFD Level 0/1 with processes P1–P6 and stores D1–D4 (Exp 8). The
build keeps these names where possible. Where the code differs from the diagrams, the difference is listed in
`03_consistency_analysis.md`.

## Additional decisions made in this build [A]
SQLite persistence (write-through), scrypt hashing, session tokens with 30-minute idle timeout, audit log table,
notification table, `Report` data kept as a table attached to reviews, single `users` table with a `role` column
instead of separate Student/Administrator tables, category-specific attributes stored as a JSON `details` column,
listing archive flag, spam/profanity word list, search result limit of 50, masked emails in the admin student list.
