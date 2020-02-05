LIB := lib

all: bdist_wheel

requirements: requirements.txt
	pip install -r requirements.txt

sdist:
	python setup.py sdist

bdist_wheel:
	# Mocking environment to enable creating wheel
	# without exporting environment variables
	TMP=$$(mktemp -d --suffix .fio-wheel-build) ;\
	echo $$TMP ;\
	mkdir -p "$$TMP/data" ;\
	mkdir -p "$$TMP/cache" ;\
	mkdir -p "$$TMP/log" ;\
	echo "DATA_PATH = \"$$TMP/data\"" >> "$$TMP/config.cfg" ;\
	echo "ERROR_LOG = \"$$TMP/log/error.log\"" >> "$$TMP/config.cfg" ;\
	echo "CACHE_PATH = \"$$TMP/cache\"" >> "$$TMP/config.cfg" ;\
	echo "DATABASE = \"sqlite:///$$TMP/data/database.db\"" >> "$$TMP/config.cfg" ;\
	export FIOWEBVIEWER_SETTINGS="$$TMP/config.cfg" ;\
	python setup.py bdist_wheel --universal ;\
	rm -rf "$$TMP"

requirements_to_wheels:
	pip wheel -r requirements.txt

git_hooks:
	@if ! [[ -L .git/hooks/pre-commit ]]; then \
        echo "Installing git pre-commit hook"; \
        ln -fs ../../git/pre-commit .git/hooks/pre-commit; \
    fi

develop: requirements git_hooks
	python setup.py develop


.PHONY: all sdist develop bdist_wheel git_hooks requirements requirements_to_wheels
