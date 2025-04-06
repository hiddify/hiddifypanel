.ONESHELL:
ENV_PREFIX=$(shell python -c "if __import__('pathlib').Path('.venv/bin/pip').exists(): print('.venv/bin/')")
USING_POETRY=$(shell grep "tool.poetry" pyproject.toml && echo "yes")

.PHONY: help
help:             ## Show the help.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep

.PHONY: prepare
prepare:             ## Show the help.
	cd scripts
	./update_translations.sh


update_req:
	upgrade-requirements 
	python scripts/update_dependencies.py


.PHONY: show
show:             ## Show the current environment.
	@echo "Current environment:"
	@if [ "$(USING_POETRY)" ]; then poetry env info && exit; fi
	@echo "Running using $(ENV_PREFIX)"
	@$(ENV_PREFIX)python -V
	@$(ENV_PREFIX)python -m site

.PHONY: install
install:          ## Install the project in dev mode.
	@if [ "$(USING_POETRY)" ]; then poetry install && exit; fi
	@echo "Don't forget to run 'make virtualenv' if you got errors."
	$(ENV_PREFIX)pip install -e cython .[test]

.PHONY: fmt
fmt:              ## Format code using black & isort.
	# $(ENV_PREFIX)isort hiddifypanel/
	# $(ENV_PREFIX)black -l 79 hiddifypanel/
	# $(ENV_PREFIX)black -l 79 tests/
	@echo skip

.PHONY: lint
lint:             ## Run pep8, black, mypy linters.
	# $(ENV_PREFIX)flake8 hiddifypanel/
	# $(ENV_PREFIX)black -l 79 --check hiddifypanel/
	# $(ENV_PREFIX)black -l 79 --check tests/
	# $(ENV_PREFIX)mypy --ignore-missing-imports hiddifypanel/
	@echo skip

.PHONY: test
test: lint        ## Run tests and generate coverage report.
	# $(ENV_PREFIX)pytest -v --cov-config .coveragerc --cov=hiddifypanel -l --tb=short --maxfail=1 tests/
	# $(ENV_PREFIX)coverage xml
	# $(ENV_PREFIX)coverage html
	@echo skip

.PHONY: watch
watch:            ## Run tests on every change.
	ls **/**.py | entr $(ENV_PREFIX)pytest -s -vvv -l --tb=long --maxfail=1 tests/

.PHONY: clean
clean:            ## Clean unused files.
	@find ./ -name '*.pyc' -exec rm -f {} \;
	@find ./ -name '__pycache__' -exec rm -rf {} \;
	@find ./ -name 'Thumbs.db' -exec rm -f {} \;
	@find ./ -name '*~' -exec rm -f {} \;
	@rm -rf .cache
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf build
	@rm -rf dist
	@rm -rf *.egg-info
	@rm -rf htmlcov
	@rm -rf .tox/
	@rm -rf docs/_build

.PHONY: virtualenv
virtualenv:       ## Create a virtual environment.
	@if [ "$(USING_POETRY)" ]; then poetry install && exit; fi
	@echo "creating virtualenv ..."
	@rm -rf .venv
	@python3 -m venv .venv
	@./.venv/bin/pip install -U pip
	@./.venv/bin/pip install -e .[test]
	@echo
	@echo "!!! Please run 'source .venv/bin/activate' to enable the environment !!!"

.PHONY: dev
dev:          ## Create a new tag for release.
	@echo "dev" > hiddifypanel/VERSION
	@echo "__version__='dev'" > hiddifypanel/VERSION.py
	@gitchangelog > HISTORY.md
	@git add hiddifypanel/VERSION hiddifypanel/VERSION.py HISTORY.md
	@git commit -m "release: switch to develop"
	@git push -u origin HEAD
.PHONY: release
release:
ifeq ($(TAG),)
	# @echo "previous tag was $$(git describe --tags $$(git rev-list --tags --max-count=1))"
	# @echo "release last version $$(lastversion hiddifypanel)"
	# @echo "beta last version $$(lastversion --pre hiddifypanel)"
	@echo "WARNING: This operation will create s version tag and push to github"
	@read -p "Version? (provide the next x.y.z semver) : " TAG
endif
	@echo "$${TAG}" > hiddifypanel/VERSION
	@sed -i "/^version =/c version = '$${TAG}'" pyproject.toml
	@sed -i "/^__version__ =/c __version__ = '$${TAG}'" pyproject.toml
	@sed -i "/^__release_time__/c __release_time__= datetime.strptime('$$(date +%Y-%m-%dT%H:%M:%S)','%Y-%m-%dT%H:%M:%S')" hiddifypanel/VERSION.py
	@git tag v$${TAG}
	@gitchangelog > HISTORY.md
	@git tag -d v$${TAG}
	@make prepare
	@git add hiddifypanel/VERSION hiddifypanel/VERSION.py HISTORY.md hiddifypanel/templates/fake.html pyproject.toml
	@git add hiddifypanel/translations/* hiddifypanel/translations.i18n/*
	@git commit -m "release: version $${TAG} 🚀"
	@echo "creating git tag : $${TAG}"
	@git tag v$${TAG}
	@git push -u origin HEAD --tags
	@echo "Github Actions will detect the new tag and release the new version."

.PHONY: docs
docs:             ## Build the documentation.
	@echo "building documentation ..."
	@$(ENV_PREFIX)mkdocs build
	URL="site/index.html"; xdg-open $$URL || sensible-browser $$URL || x-www-browser $$URL || gnome-open $$URL

.PHONY: switch-to-poetry
switch-to-poetry: ## Switch to poetry package manager.
	@echo "Switching to poetry ..."
	@if ! poetry --version > /dev/null; then echo 'poetry is required, install from https://python-poetry.org/'; exit 1; fi
	@rm -rf .venv
	@poetry init --no-interaction --name=a_flask_test --author=rochacbruno
	@echo "" >> pyproject.toml
	@echo "[tool.poetry.scripts]" >> pyproject.toml
	@echo "hiddifypanel = 'hiddifypanel.__main__:main'" >> pyproject.toml 
	@cat requirements.txt | while read in; do poetry add --no-interaction "$${in}"; done
	@cat requirements-base.txt | while read in; do poetry add --no-interaction "$${in}" --dev; done
	@cat requirements-test.txt | while read in; do poetry add --no-interaction "$${in}" --dev; done
	@poetry install --no-interaction
	@mkdir -p .github/backup
	@mv requirements* .github/backup
	@mv setup.py .github/backup
	@echo "You have switched to https://python-poetry.org/ package manager."
	@echo "Please run 'poetry shell' or 'poetry run hiddifypanel'"
	
	
# This project has been generated from rochacbruno/flask-project-template
# __author__ = 'rochacbruno'
# __repo__ = https://github.com/rochacbruno/flask-project-template
# __sponsor__ = https://github.com/sponsors/rochacbruno/



stress_test:
	echo "GET http://localhost:9000/x2hDG4gt32VDbuZsYY6iq/c9c0c597-f42c-44d8-96e1-81f91dbcf1d0/singbox/?asn=unknown" | vegeta attack -duration=5s | tee results.bin | vegeta report	



protos:
	python3 -m grpc.tools.protoc --pyi_out=./ -I ./ --python_out=./ --grpc_python_out=./  $$(find . -name "*.proto")

	sed -i "s/_registered_method=True//g" $$(find . -name "*_pb2_grpc.py")

