REQUIREMENTS             := requirements.txt
SHELL                    := /bin/bash
VIRTUAL_ENV              ?= venv

# PHONY just means this target does not make any files
.PHONY: setup clean test help

default: help

# Make sure the virtualenv exists, create it if not.
$(VIRTUAL_ENV):
	python3 -m venv $(VIRTUAL_ENV)

# Check for the existence/timestamp of .reqs-installed if the
# file is missing or older than the requirements.txt this will run pip
$(VIRTUAL_ENV)/.reqs-installed: $(REQUIREMENTS)
	$(VIRTUAL_ENV)/bin/pip install -r $(REQUIREMENTS)
	touch $(VIRTUAL_ENV)/.reqs-installed

setup: $(VIRTUAL_ENV) $(VIRTUAL_ENV)/.reqs-installed ## Setup local environment

clean: ## Clean your local workspace
	rm -rf $(VIRTUAL_ENV)
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf *.egg-info
	find . -name '*.py[co]' -delete

test: setup
	$(VIRTUAL_ENV)/bin/pytest

format:
	$(VIRTUAL_ENV)/bin/black .

run: setup
	$(VIRTUAL_ENV)/bin/python -m dashboard

help: ## Show the available commands
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | awk -F ':.*?## ' 'NF==2 {printf "   %-20s%s\n", $$1, $$2}' | sort
