# Canonical entrypoints for humans, agents and CI alike (see AGENTS.md).
# Adopting projects replace the bodies with their real setup/verification;
# target names and semantics stay the same so agent instructions keep working.

.DEFAULT_GOAL := help
.PHONY: help setup test e2e adopt reconcile

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup: ## One-time local setup (extend per project)
	pip install knowform

test: ## Full verification - the gate before every commit (extend per project)
	python3 -m unittest discover -s framework/scripts -p "test_*.py"

e2e: ## Black-box e2e against the shippable artifact (fill in per project)
	@echo "no e2e suite defined yet - see AGENTS.md 'Commands'" && exit 1

adopt: ## Copy the scaffold into TARGET, never overwriting (make adopt TARGET=/path/to/repo)
	python3 framework/scripts/adopt.py $(TARGET)

reconcile: ## Report doc↔code drift (read-only; non-blocking until the judge is trusted, framework/docs/adr/0003 M4)
	knowform plan --format summary
