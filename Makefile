#% _________________________________________________
#%  _____ _____ _____ _____ _____ _____ _____ _____
#% |   __|   __|  _  |_   _|  |  | __  |   __|   __|
#% |   __|   __|     | | | |  |  |    -|   __|__   |
#% |__|  |_____|__|__| |_| |_____|__|__|_____|_____|
#% _________________________________________________
#%
#% Tools for building, running, and testing cannula
#%
#% Usage:
#%   make <command>
#%
#% Start up the developer tools locally:
#%   make build
#%   make dev
#%
#% Run the tests locally (requires Python >= 3.6):
#%   make test
#%

ARCH                     := $(shell uname -s)
REQUIREMENTS             := $(shell cat requirements*)
SHELL                    := /bin/bash
VIRTUAL_ENV              ?= .venv
PYTHON_MODULES           := $(shell find . -name '*.py')
DOCKER_COMPOSE           := $(shell which docker-compose)

# Generate the MD5SUM of the requirements files.
# Mac and Linx have slightly different md5 commands, hense the ARCH check.
ifeq ("${ARCH}", "Darwin")
	MD5SUM := $(shell md5 -q -s "${REQUIREMENTS}")
else
	MD5SUM := $(shell echo "${REQUIREMENTS}" | md5sum | cut -d ' ' -f1)
endif

.SILENT: help
.PHONY: setup build run dev docs clean
.PHONY: test flake8 unit inttest integration
.PHONY: help

default: help

# Make sure the virtualenv exists, create it if not.
$(VIRTUAL_ENV):
	python3 -m venv $(VIRTUAL_ENV)

# Check for the existence of reqs-(md5) and run pip install if missing.
$(VIRTUAL_ENV)/reqs-$(MD5SUM):
	$(VIRTUAL_ENV)/bin/pip install -r requirements-test.txt
	touch $(VIRTUAL_ENV)/reqs-$(MD5SUM)

setup: $(VIRTUAL_ENV) $(VIRTUAL_ENV)/reqs-$(MD5SUM) ## Setup local environment

clean: ## Clean your local workspace
	rm -rf $(VIRTUAL_ENV)
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf *.egg-info
	find . -name '__pycache__' -delete
	find . -name '*.pyc' -delete

test: flake8 unit ## Run the tests (flake8, unit)

flake8: setup ## Run flake8 checks
	$(VIRTUAL_ENV)/bin/flake8 cannula tests

unit: setup ## Run unit tests
	$(VIRTUAL_ENV)/bin/coverage erase
	FAKE_MODE=True UNITTEST_RUN=True CACHE_URL=cache://localhost $(VIRTUAL_ENV)/bin/coverage run --branch --source=cannula -m unittest
	$(VIRTUAL_ENV)/bin/coverage html
	$(VIRTUAL_ENV)/bin/coverage report -m --fail-under=100

.coverage: $(PYTHON_MODULES)
	@touch .coverage # Create the .coverage file to catch errors in test setup
	@$(MAKE) test

run-tests: .coverage

watch:  ## Watch for changes to python modules and re-run the tests
	@rm -f .coverage
	@while true; do $(MAKE) --no-print-directory -q run-tests || $(MAKE) run-tests; sleep 0.5; done

#% Available Commands:
help: ## Help is on the way
	grep '^#%' $(MAKEFILE_LIST) | sed -e 's/#%//'
	grep '^[a-zA-Z]' $(MAKEFILE_LIST) | awk -F ':.*?## ' 'NF==2 {printf "   %-20s%s\n", $$1, $$2}' | sort
