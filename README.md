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
## RSS

Opt in with `blarg build --site-url https://example.test/blog/ --feed-title "My blog"`.
The equivalent Python API is `build_site(source, target, site_url="https://example.test/blog/", feed_title="My blog")`.
Without `site_url`, no feed is generated. Supply your deployed HTTP(S) base URL,
including any path prefix. RSS is written to `rss.xml`; that output is reserved
when enabled. URLs with credentials, query strings, fragments or dot path segments
are rejected before output is cleared, as are invalid feed titles and malformed
percent escapes. Valid percent-encoded path characters are preserved, including
encoded slashes, so the deployed prefix is not reinterpreted. This introduces
no configuration file, network requests, automatic domain detection or dependency.

Implementation choices for issue #4:

- The channel title and description use `feed_title` (default `Blarg`). The channel
  link is the supplied base URL, normalized with a trailing slash.
- Entries are successfully built Markdown pages recursively beneath `blog/` or
  `posts/` directly inside the source root. Frontmatter `type` is ignored, following
  the maintainer's later directory-based design in issue #9 rather than the older
  content-type wording in issue #4. A nested `other/posts/` is not a blog directory.
  Boolean `published: false` excludes a post
  from the feed only, not from the normal site build. Other pages are not included.
- For duplicate flat output names, the last successful writer owns the entry,
  even if it is outside the blog directories. A later failed parse preserves the previous entry.
- Titles use a nonblank string title or the source filename stem. XML-special
  characters are escaped; XML 1.0 forbidden characters are removed from titles.
  Links and permalink GUIDs encode the actual output path beneath the base URL,
  never a local absolute path or the frontmatter slug.
- Valid timezone-aware ISO datetime strings or YAML datetimes supply UTC RFC 822
  publication dates. Missing, invalid, date-only and timezone-naive dates omit
  `pubDate`; conversion outside representable UTC also omits it. No timezone is guessed. Newest dated posts come first, then undated
  posts. Ties sort by output URL. An empty selection produces a valid empty feed.
- Rebuilds replace the feed along with other generated output; disabling RSS on
  the next build removes it. The feed is not counted as an input page or added to
  the global article index. Existing content discovery and collision policy are
  otherwise unchanged.
