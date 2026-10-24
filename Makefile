.PHONY: run test lint fmt typecheck docker
run:        ; PYTHONPATH=src python3 -m srp
test:       ; pytest --cov=srp --cov-report=term-missing
lint:       ; ruff check src tests && ruff format --check src tests
fmt:        ; ruff check --fix src tests && ruff format src tests
typecheck:  ; mypy src
docker:     ; docker build -t srp .
