# Blarg README

A static site generator

## Installation:

```
git clone git@github.com:pydanny/blarg.git
cd blarg
pip install -e .
```

## Building:

```
blarg build .
```


## Serving the site:

```
blarg serve
```

## Release to PyPI

Create a pull request that:

1. Adds release notes to `CHANGELOG.md`.

2. Updates the `VERSION` constant in `pyproject.toml` and .

Commit these changes in a single commit with subject matching
`Bump version to v...`.

After merging the pull request, push an annotated tag to Github with:

```sh
make tag
```

This will trigger a Github action to publish the package to PyPI.

Note: Until we're configured, just do this to release:

```
pip install -U build twine
python -m build
twine upload dist/*
```