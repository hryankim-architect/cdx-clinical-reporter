# cdx-clinical-reporter -- regulated CDx-reporting clean-room demo.
# Reproducible end-to-end with: make install && make run && make test

PYTHON ?= python3
PKG := cdxreport
RUN_NAME ?= demo
ARTIFACT_DIR := artifacts

.PHONY: help install data run test lint clean canary

help:
	@echo "make install      Install pinned dependencies (uv sync, or pip -e .)"
	@echo "make data         No-op for the synthetic demo; prints the regulated patterns modeled"
	@echo "make run          Run the end-to-end signed-report pipeline (audit + MLflow hooks)"
	@echo "make test         Run pytest"
	@echo "make lint         ruff check"
	@echo "make canary       Run the deterministic canary smoke test"
	@echo "make  Check the honest-scope preamble is present in README"
	@echo "make clean        Remove build artifacts"

install:
	uv sync --extra dev || $(PYTHON) -m pip install -e ".[dev]"

data:
	$(PYTHON) -m $(PKG).pipeline fetch

run: | $(ARTIFACT_DIR)
	$(PYTHON) -m $(PKG).pipeline run --name $(RUN_NAME) --out $(ARTIFACT_DIR)

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check src tests

canary:
	$(PYTHON) -m $(PKG).canary


clean:
	rm -rf $(ARTIFACT_DIR) .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

$(ARTIFACT_DIR):
	mkdir -p $@
