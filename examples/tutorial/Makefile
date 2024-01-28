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
	rm -f db.sqlite
	find . -name '*.py[co]' -delete

test: setup  ## Test the code
	DATABASE_URI="sqlite+aiosqlite:///:memory:" $(VIRTUAL_ENV)/bin/pytest --cov dashboard --cov-config=setup.cfg

format:  ## Format the code with ruff
	$(VIRTUAL_ENV)/bin/ruff format dashboard tests

run: setup  ## Run the application
	$(VIRTUAL_ENV)/bin/python -m dashboard run

initdb: setup  ## Create database tables
	$(VIRTUAL_ENV)/bin/python -m dashboard initdb

help: ## Show the available commands
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | awk -F ':.*?## ' 'NF==2 {printf "   %-20s%s\n", $$1, $$2}' | sort
