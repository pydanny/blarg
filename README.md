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


## Tags

Markdown frontmatter can include a YAML list such as `tags: [python, howto]`.
Builds generate `tags/index.html`, using the selected Markdown layout, with one
group per tag and links to successfully rendered Markdown pages. The page title
is `Tags`. Visit `/tags/` on the built site; this does not change the global index.

These are implementation choices for the tagging feature:

- A single string is also accepted as one tag, including strings with spaces.
  Surrounding whitespace is stripped. Case and Unicode spelling are preserved;
  no Unicode normalization or comma splitting is performed.
- Empty strings and non-string list entries are ignored. Missing, null, numeric
  or mapping-valued tags are ignored. Duplicate tags on a page appear only once.
- Groups sort by tag text, case-sensitively. Within each group, pages sort by
  their source-relative POSIX path, also case-sensitively, not by date.
- Link labels use a nonblank string title, otherwise the source filename stem.
  Labels and tag names are HTML-escaped; links encode the existing output path.
  Tags do not become filenames and no per-tag URLs are introduced.
- If multiple sources write the same flat output path, only the last successful
  write supplies that output's tags and title. A later failed page does not erase
  an earlier successful entry. This does not change existing collision handling.
- With no valid tags, no tag index is generated. A custom output already at
  `tags/index.html` takes precedence, including the normal output of `tags.md`.
  Builds replace the output directory, so customize source files, not generated
  output. The tag index is not counted as an input page.

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
