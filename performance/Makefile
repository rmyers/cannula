
REQUIREMENTS             := $(shell find .. -name 'pyproject.toml')
SHELL                    := /bin/bash
VIRTUAL_ENV              := venv

.SILENT: help
.PHONY: setup docs clean
.PHONY: test flake8 unit
.PHONY: publish publish-test
.PHONY: help

default: help

# Make sure the virtualenv exists, create it if not.
$(VIRTUAL_ENV):
	python3 -m venv $(VIRTUAL_ENV)

# Check for the existence of reqs-(md5) and run pip install if missing.
$(VIRTUAL_ENV)/.requirements-installed: $(REQUIREMENTS)
	$(VIRTUAL_ENV)/bin/pip install -e ..[performance]
	touch $(VIRTUAL_ENV)/.requirements-installed

setup: $(VIRTUAL_ENV) $(VIRTUAL_ENV)/.requirements-installed ## Setup local environment

clean: ## Clean your local workspace
	rm -rf $(VIRTUAL_ENV)

test: setup ## run performance test
	$(VIRTUAL_ENV)/bin/pytest --no-cov -s test_performance.py

#% Available Commands:
help: ## Help is on the way
	grep '^#%' $(MAKEFILE_LIST) | sed -e 's/#%//'
	grep '^[a-zA-Z]' $(MAKEFILE_LIST) | awk -F ':.*?## ' 'NF==2 {printf "   %-20s%s\n", $$1, $$2}' | sort
