from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

import yaml

from blarg.main import build_site


class Index(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.groups = {}
        self.current = None
        self.heading = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == "h2":
            self.heading = True
        if tag == "a":
            self.groups[self.current].append(dict(attrs)["href"])

    def handle_data(self, text):
        if self.heading:
            self.current = text
            self.groups[text] = []

    def handle_endtag(self, tag):
        if tag == "h2":
            self.heading = False


def page(source, name, **metadata):
    path = source / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"title": "Article", **metadata}) + "---\nBody")
    return path


def index(target):
    path = target / "tags/index.html"
    assert path.is_file(), "Tagged builds should generate a tag index"
    return Index(path.read_text()).groups


def test_grouping_is_deterministic_and_links_resolve(tmp_path):
    source, target = tmp_path / "source", tmp_path / "site"
    page(source, "posts/z.md", tags=["python", "travel", "python"])
    page(source, "blog/a.md", tags=["python"])
    build_site(source, target)
    assert index(target) == {"python": ["../a/", "../z/"], "travel": ["../z/"]}
    assert list(index(target)) == ["python", "travel"]
    for links in index(target).values():
        for href in links:
            assert (
                target / "tags" / unquote(urlsplit(href).path) / "index.html"
            ).is_file()


def test_mixed_missing_and_scalar_metadata(tmp_path):
    source, target = tmp_path / "source", tmp_path / "site"
    page(
        source,
        "mixed.md",
        tags=[" python ", "", None, 7, True, ["nested"], {"bad": 1}, "python"],
    )
    page(source, "scalar.md", tags="martial arts")
    for name, tags in [("mapping", {"bad": 1}), ("number", 4), ("null", None)]:
        page(source, name + ".md", tags=tags)
    page(source, "missing.md")
    build_site(source, target)
    assert index(target) == {"martial arts": ["../scalar/"], "python": ["../mixed/"]}


def test_escaping_and_encoding(tmp_path):
    source, target = tmp_path / "source", tmp_path / "site"
    page(
        source,
        'posts/a #?%"日本.md',
        tags=['<script>&"'],
        title="<img src=x onerror=alert(1)>",
    )
    build_site(source, target)
    assert index(target) == {'<script>&"': ["../a%20%23%3F%25%22%E6%97%A5%E6%9C%AC/"]}
    text = (target / "tags/index.html").read_text()
    assert "<script>" not in text and "<img " not in text
    assert "&lt;script&gt;" in text and "&lt;img " in text


def test_only_successful_markdown_and_repeated_builds(tmp_path):
    source, target = tmp_path / "source", tmp_path / "site"
    good = page(source, "good.md", tags=["first"])
    page(source, "node_modules/skip.md", tags=["skipped"])
    bad = page(source, "bad.md", tags=["bad"])
    bad.write_text("title: [\ntags: [bad]\n---\nBody")
    build_site(source, target)
    assert index(target) == {"first": ["../good/"]}
    page(source, "good.md", tags=["second"])
    build_site(source, target)
    assert index(target) == {"second": ["../good/"]}
    good.unlink()
    build_site(source, target)
    assert not (target / "tags/index.html").exists()


def test_custom_markdown_index_wins(tmp_path):
    source, target = tmp_path / "source", tmp_path / "site"
    page(source, "tags.md", title="Custom tags")
    page(source, "article.md", tags=["python"])
    build_site(source, target)
    text = (target / "tags/index.html").read_text()
    assert "<title>Custom tags</title>" in text
    assert "<h2>python</h2>" not in text


def test_no_tags_does_not_generate_index(tmp_path):
    source, target = tmp_path / "source", tmp_path / "site"
    page(source, "article.md")
    build_site(source, target)
    assert not (target / "tags/index.html").exists()


def test_duplicate_flat_outputs_follow_last_successful_write(tmp_path, monkeypatch):
    from pathlib import Path

    import pytest

    import blarg.main as main

    source, target = tmp_path / "source", tmp_path / "site"
    first = page(source, "z/article.md", tags=["old"], title="Old")
    last = page(source, "a/article.md", tags=["new"], title="New")
    if hasattr(main, "_check_destinations"):
        # PR14 rejects the collision before cleanup rather than allowing winners.
        with pytest.raises(ValueError, match="Conflicting output path"):
            build_site(source, target)
        assert not target.exists()
        return
    # The real builder's discovery order controls overwrites, not tag sort order.
    monkeypatch.setattr(Path, "rglob", lambda self, pattern: iter([first, last]))
    build_site(source, target)
    assert index(target) == {"new": ["../article/"]}
    assert ">New</a>" in (target / "tags/index.html").read_text()
    last.write_text("title: [\n---\nBad")
    build_site(source, target)
    assert index(target) == {"old": ["../article/"]}
    assert ">Old</a>" in (target / "tags/index.html").read_text()
    page(source, "a/article.md", title="Untagged winner")
    build_site(source, target)
    assert not (target / "tags/index.html").exists()


def test_selected_template_and_title_fallback(tmp_path, monkeypatch):
    from jinja2 import DictLoader, Environment

    import blarg.main as main

    monkeypatch.setattr(
        main,
        "template_env",
        Environment(
            loader=DictLoader(
                {"custom.html": "CUSTOM {{ frontmatter.title }} {{ body }}"}
            )
        ),
    )
    source, target = tmp_path / "source", tmp_path / "site"
    page(source, "article.md", tags=["python"], title=None)
    build_site(source, target, "custom.html")
    assert index(target) == {"python": ["../article/"]}
    text = (target / "tags/index.html").read_text()
    assert text.startswith("CUSTOM Tags ")
    assert ">article</a>" in text
