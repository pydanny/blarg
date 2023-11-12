lint:
	ruff check --fix .
	ruff format .

clean:
	@echo Cleaning workspace
	-rm -rf dist/ *.egg-info/ build/
	-find . -type d -name __pycache__ -delete

# Releases

# Extract version from pyproject.toml
VERSION=$(shell python -c "import importlib.metadata; print(importlib.metadata.version('blarg'))")

tag:
	@echo Tagging as $(VERSION)
	git tag -a $(VERSION) -m "Creating version $(VERSION)"
	git push origin $(VERSION)