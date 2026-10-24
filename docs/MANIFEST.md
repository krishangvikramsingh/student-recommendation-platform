# Deliverables manifest

| Path | Purpose |
|---|---|
| `README.md` | Overview, quick start, limitations, demonstration guide |
| `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini` | Dependencies (tools only), configuration reference, ignore rules, test configuration |
| `src/srp/models.py, errors.py, security.py` | Domain objects, error types, password hashing |
| `src/srp/service.py` | Business rules (the `Platform` class) |
| `src/srp/store.py` | SQLite schema and write-through persistence |
| `src/srp/server.py, __main__.py, config.py, seed.py` | HTTP/JSON interface and sessions, start-up, settings, sample data |
| `src/srp/web/` | Browser user interface (HTML, CSS, JavaScript) |
| `tests/` | 96 automated tests |
| `scripts/smoke_check.py` | Live smoke test of a running server |
| `scripts/nfr_checks.py` | Timing, concurrency, reliability and restart measurements |
| `scripts/ui_walkthrough.py` | Browser walkthrough, click count, accessibility scan, screenshots |
| `scripts/build_report.py` | Builds the Word report (convert to PDF with LibreOffice) |
| `scripts/gen_test_report.py` | Builds `docs/test_results_generated.md` from the test run |
| `docs/01_requirements_inventory.md` | Requirements classified as documented, inferred, or decided here |
| `docs/02_traceability_matrix.md` | Requirement-to-design-to-code-to-test matrix |
| `docs/03_consistency_analysis.md` | Contradictions between the experiments and how each was handled |
| `docs/04_nfr_verification.md` | Each Experiment 2 target with measured result and limits |
| `docs/05_test_report.md`, `docs/test_results_generated.md` | Test summary and the full list of 96 results |
| `docs/06_deployment.md` | Configuration, run, test and troubleshooting steps |
| `docs/diagrams/` | PNG diagrams; `src/` holds the Python scripts that draw the architecture, use-case, sequence, collaboration and DFD figures; `class_diagram_exp5.png` and `activity_diagram_exp4.png` are the original images from Experiments 4 and 5 |
| `docs/evidence/` | pytest output, JUnit XML, smoke output, restart check, load results, UI walkthrough results, screenshots, history of the Experiment 9–10 runs |
| `report/` | Project report in Word and PDF |
