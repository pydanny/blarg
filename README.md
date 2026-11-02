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

### HTML pages

Alongside Markdown, the builder renders `.html` source files as complete Jinja2
templates. HTML keeps its path relative to the source directory: for example,
`about.html` becomes `site/about.html`, and `docs/example.html` becomes
`site/docs/example.html`.

```html
<!doctype html>
<title>Example</title>
{% for number in [1, 2, 3] %}
<p>Item {{ number }}</p>
{% endfor %}
```

HTML uses the existing Jinja environment, including autoescaping and the
package-then-`templates/` lookup order for local includes and inheritance.
`templates/` is relative to the working directory, as before. HTML is not passed
through Markdown or wrapped in the default Markdown layout; it introduces no
frontmatter format or additional context variables. Use trusted templates only:
the Jinja environment is not a sandbox. This does not add `.bmd` or Python-block
execution, or remote template loaders.

Markdown keeps its existing frontmatter, layout and output path:
`nested/article.md` still becomes `site/article/index.html`. The generated index
still lists Markdown articles. Hidden files/directories, `templates/`,
`node_modules/`, symbolic links and the output subtree are not scanned as content.

The generated `index.html` and `public/pygments.css` are reserved. A conflicting
HTML or Markdown destination (including a file where another output needs a
directory) raises `ValueError` **before** the output directory is cleared. For
example, `article.md` and `article/index.html` conflict, but `article.md` and
`article.html` do not. An HTML syntax or include error also leaves existing output
untouched. Valid builds still replace the output directory; keep it separate from
your source and other valuable data. The source itself, its ancestors and symbolic
links cannot be used as the output directory.

### Tests

With the project dependencies installed, run the build regression suite without
starting a server:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

The tests build only in fresh temporary directories.


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
