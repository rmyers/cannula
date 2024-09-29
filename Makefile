#% _________________________________________________
#%      _________    _   ___   ____  ____    ___
#%     / ____/   |  / | / / | / / / / / /   /   |
#%    / /   / /| | /  |/ /  |/ / / / / /   / /| |
#%   / /___/ ___ |/ /|  / /|  / /_/ / /___/ ___ |
#%   \____/_/  |_/_/ |_/_/ |_/\____/_____/_/  |_|
#% _________________________________________________
#%
#% Tools for building, running, and testing cannula.
#%
#% Usage:
#%   make <command>
#%
#% Getting Started:
#%   make setup
#%
#% Run the tests locally (requires Python >= 3.6):
#%   make test
#%

REQUIREMENTS             := $(shell find . -name 'pyproject.toml')
SHELL                    := /bin/bash
VIRTUAL_ENV              ?= venv
PYTHON_MODULES           := $(shell find . -name '*.py')
DOCKER_COMPOSE           := $(shell which docker-compose)

export HATCH_INDEX_USER = __token__
export RUFF_CMD = $(VIRTUAL_ENV)/bin/ruff

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
	$(VIRTUAL_ENV)/bin/pip install -e .[test,httpx]
	touch $(VIRTUAL_ENV)/.requirements-installed

reports:
	mkdir -p reports

setup: reports $(VIRTUAL_ENV) $(VIRTUAL_ENV)/.requirements-installed ## Setup local environment

clean: ## Clean your local workspace
	rm -rf $(VIRTUAL_ENV)
	rm -rf htmlcov .coverage reports
	rm -rf *.egg-info
	rm -rf build dist .*_cache *.egg-info
	find . -name '*.py[co]' -delete
	find . -name '__pycache__' -delete

test: flake8 unit ## Run the tests (flake8, unit)

flake8: setup ## Run flake8 checks
	$(VIRTUAL_ENV)/bin/flake8 cannula tests

unit: setup ## Run unit tests
	$(VIRTUAL_ENV)/bin/pytest

mypy: setup ## Run mypy on code
	$(VIRTUAL_ENV)/bin/mypy cannula

.coverage: $(PYTHON_MODULES)
	@touch .coverage # Create the .coverage file to catch errors in test setup
	@$(MAKE) test

run-tests: .coverage

watch:  ## Watch for changes to python modules and re-run the tests
	@rm -f .coverage
	@while true; do $(MAKE) --no-print-directory -q run-tests || $(MAKE) run-tests; sleep 5; done

docs: setup  ## Build the documentation
	$(VIRTUAL_ENV)/bin/sphinx-build -a docs docs/_build

publish-test: setup  ## Publish the library to test pypi
	$(VIRTUAL_ENV)/bin/hatch build -t sdist -t wheel
	$(VIRTUAL_ENV)/bin/hatch publish --repo https://test.pypi.org/legacy/

publish: setup  ## Publish the library to pypi
	$(VIRTUAL_ENV)/bin/hatch build -t sdist -t wheel
	$(VIRTUAL_ENV)/bin/hatch publish

format:
	$(VIRTUAL_ENV)/bin/black .

#% Available Commands:
help: ## Help is on the way
	grep '^#%' $(MAKEFILE_LIST) | sed -e 's/#%//'
	grep '^[a-zA-Z]' $(MAKEFILE_LIST) | awk -F ':.*?## ' 'NF==2 {printf "   %-20s%s\n", $$1, $$2}' | sort
