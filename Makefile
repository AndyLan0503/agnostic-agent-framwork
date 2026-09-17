# Canonical entrypoints for humans, agents and CI alike (see AGENTS.md).
# Adopting projects replace the bodies with their real setup/verification;
# target names and semantics stay the same so agent instructions keep working.

.DEFAULT_GOAL := help
.PHONY: help setup test e2e reconcile

# The suites run on the stock macOS python3 (3.9) on purpose - AGENTS.md
# "Conventions". knowform requires >= 3.10, so the reconciler gets its own
# interpreter and virtualenv instead of dragging the floor up. Override with
# `make setup TOOLS_PYTHON=/path/to/python3.12` where the search misses.
TOOLS_PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || \
                       command -v python3.11 || command -v python3.10)
TOOLS_VENV := .venv-tools

help: ## List targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup: ## One-time local setup (extend per project)
	@test -n "$(TOOLS_PYTHON)" || { \
	  echo "no Python >= 3.10 found for knowform; install one or pass" >&2; \
	  echo "TOOLS_PYTHON=/path/to/python3.1x" >&2; exit 1; }
	$(TOOLS_PYTHON) -m venv $(TOOLS_VENV)
	$(TOOLS_VENV)/bin/pip install --quiet "knowform>=0.3,<0.4"

test: ## Full verification - the gate before every commit (extend per project)
	python3 -m unittest discover -s framework/scripts -p "test_*.py"

e2e: ## Black-box e2e against the shippable artifact (fill in per project)
	@echo "no e2e suite defined yet - see AGENTS.md 'Commands'" && exit 1

reconcile: ## Report doc↔code drift (read-only; non-blocking until the judge is trusted)
	$(TOOLS_VENV)/bin/knowform plan --format summary
