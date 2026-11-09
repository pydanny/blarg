# Blarg README

A static site generator

## Features

- Fast
- Simple
- Easy

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


## Not-found page

Builds generate `site/404.html` using the selected Markdown layout, with the title
`404 - Blarg` and a self-contained robot illustration. The generated page is not
added to the article index or the count of built input files.

A custom page already built at `404.html` or `404/index.html` takes precedence:
no default page is added. In particular, `404.md` keeps the normal Markdown
mapping to `404/index.html`; it is not copied or redirected to `404.html`.
Each build still replaces the output directory, so customize source content,
not files in the generated site.

Configure your hosting provider to use the appropriate generated file for missing
URLs. This does not change `blarg serve` or `serve2`, and does not configure HTTP
404 fallback routing or status codes automatically.

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