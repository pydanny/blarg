from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import yaml

from blarg.main import build_site


def page(source, name, **meta):
    p = source / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump({"title": "Post", **meta}) + "---\nBody",
        encoding="utf-8",
    )
    return p


def feed(target):
    return ET.parse(target / "rss.xml").getroot()


def test_default_off_and_opt_in(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    page(src, "posts/p.md")
    build_site(src, out)
    assert not (out / "rss.xml").exists()
    build_site(
        src, out, site_url="https://example.test/blog", feed_title="News & <updates>"
    )
    root = feed(out)
    assert root.attrib == {"version": "2.0"}
    assert root.findtext("channel/title") == "News & <updates>"
    assert root.findtext("channel/link") == "https://example.test/blog/"
    assert root.findtext("channel/description")
    item = root.find("channel/item")
    assert (
        item.findtext("link") == item.findtext("guid") == "https://example.test/blog/p/"
    )
    assert item.findtext("title") == "Post"
    assert item.find("pubDate") is None


def test_membership_dates_encoding_rebuild(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    page(src, "posts/a #?%日本.md", title="<A & B>", date="2024-01-02T01:00:00+01:00")
    page(src, "blog/nested/old.md", date="2023-01-01T00:00:00Z")
    page(src, "posts/naive.md", date="2025-01-01T00:00:00")
    page(src, "posts/bad-date.md", date=["invalid"], title=None)
    page(src, "guide.md", type="page")
    page(src, "posts/draft.md", published=False)
    page(src, "posts/node_modules/skip.md")
    page(src, "posts/broken.md").write_text("title: [\n---\nBroken")
    build_site(src, out, site_url="https://example.test/base/")
    items = feed(out).findall("channel/item")
    assert [x.findtext("title") for x in items] == [
        "<A & B>",
        "Post",
        "bad-date",
        "Post",
    ]
    assert (
        items[0].findtext("link")
        == "https://example.test/base/a%20%23%3F%25%E6%97%A5%E6%9C%AC/"
    )
    assert items[0].findtext("pubDate") == "Tue, 02 Jan 2024 00:00:00 GMT"
    assert items[2].find("pubDate") is None
    for item in items:
        assert str(tmp_path) not in ET.tostring(item, encoding="unicode")
    for p in src.rglob("*.md"):
        p.unlink()
    build_site(src, out, site_url="https://example.test/")
    assert feed(out).findall("channel/item") == []
    build_site(src, out)
    assert not (out / "rss.xml").exists()


@pytest.mark.parametrize(
    "url",
    [
        "",
        "/relative",
        "ftp://example.test",
        "https://",
        "https://user:pass@example.test",
        "https://example.test/?q=1",
        "https://example.test/#f",
        "https://example.test:bad",
        "https://exa mple.test",
        "https://example.test/../a",
        "https://example.test/%2e%2e/a",
        "https://example.test/\n",
    ],
)
def test_invalid_url_preserves_output(tmp_path, url):
    src, out = tmp_path / "src", tmp_path / "out"
    page(src, "posts/p.md")
    out.mkdir()
    (out / "keep").write_text("safe")
    with pytest.raises(ValueError):
        build_site(src, out, site_url=url)
    assert (out / "keep").read_text() == "safe"


@pytest.mark.parametrize("title", ["", " ", None, 3, "bad\x00title"])
def test_invalid_title_preserves_output(tmp_path, title):
    src, out = tmp_path / "src", tmp_path / "out"
    page(src, "posts/p.md")
    out.mkdir()
    (out / "keep").write_text("safe")
    with pytest.raises(ValueError):
        build_site(src, out, site_url="https://example.test", feed_title=title)
    assert (out / "keep").read_text() == "safe"


def test_last_successful_writer(tmp_path, monkeypatch):
    src, out = tmp_path / "src", tmp_path / "out"
    first = page(src, "posts/z/p.md", title="first")
    last = page(src, "blog/a/p.md", title="last")
    monkeypatch.setattr(Path, "rglob", lambda self, pattern: iter([first, last]))
    build_site(src, out, site_url="https://example.test")
    assert feed(out).findtext("channel/item/title") == "last"
    last.write_text("title: [\n---\nBroken")
    build_site(src, out, site_url="https://example.test")
    assert feed(out).findtext("channel/item/title") == "first"
    outside = page(src, "outside/p.md", type="post")
    monkeypatch.setattr(Path, "rglob", lambda self, pattern: iter([first, outside]))
    build_site(src, out, site_url="https://example.test")
    assert feed(out).findall("channel/item") == []


def test_reserved_feed_destination_preserves_output(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    page(src, "rss.xml.md")
    out.mkdir()
    (out / "keep").write_text("safe")
    with pytest.raises(ValueError, match="reserved"):
        build_site(src, out, site_url="https://example.test")
    assert (out / "keep").read_text() == "safe"


def test_xml_invalid_metadata_and_yaml_timestamp(tmp_path):
    from datetime import datetime, timezone

    src, out = tmp_path / "src", tmp_path / "out"
    page(
        src,
        "posts/post.md",
        title="A\x00B\ufffeC",
        date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    build_site(src, out, site_url="https://example.test/prefix%20with%20space")
    item = feed(out).find("channel/item")
    assert item.findtext("title") == "ABC"
    assert item.findtext("pubDate") == "Mon, 01 Jan 2024 00:00:00 GMT"
    assert item.findtext("link") == "https://example.test/prefix%20with%20space/post/"


def test_default_build_compatibility(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    page(src, "post.md")
    build_site(src, out)
    assert (out / "post/index.html").is_file()
    assert not (out / "rss.xml").exists()


def test_directory_membership_replaces_types(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    page(src, "posts/no-type.md")
    page(src, "blog/deep/other-type.md", type="page")
    page(src, "elsewhere/typed.md", type="post")
    page(src, "nested/posts/not-root.md", type="post")
    page(src, "posts-suffix/no.md", type="post")
    build_site(src, out, site_url="https://example.test")
    assert [item.findtext("link") for item in feed(out).findall("channel/item")] == [
        "https://example.test/no-type/",
        "https://example.test/other-type/",
    ]


@pytest.mark.parametrize(
    "date",
    [
        "0001-01-01T00:00:00+01:00",
        "9999-12-31T23:59:59-01:00",
        "2024-02-30T00:00:00Z",
        "2024-01-01",
        None,
    ],
)
def test_unusable_date_is_omitted(tmp_path, date):
    src, out = tmp_path / "src", tmp_path / "out"
    page(src, "posts/p.md", date=date)
    build_site(src, out, site_url="https://example.test")
    item = feed(out).find("channel/item")
    assert item is not None
    assert item.find("pubDate") is None


def test_earliest_valid_date_precedes_undated(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    page(src, "posts/z-dated.md", title="dated", date="0001-01-01T00:00:00+00:00")
    page(src, "posts/a-undated.md", title="undated")
    build_site(src, out, site_url="https://example.test")
    assert [item.findtext("title") for item in feed(out).findall("channel/item")] == [
        "dated",
        "undated",
    ]


def test_encoded_reserved_prefix_preserved(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    page(src, "posts/a.md")
    build_site(src, out, site_url="https://example.test/a%2Fb/%3F%23%25/")
    root = feed(out)
    assert root.findtext("channel/link") == "https://example.test/a%2Fb/%3F%23%25/"
    assert (
        root.findtext("channel/item/link") == "https://example.test/a%2Fb/%3F%23%25/a/"
    )
    assert root.findtext("channel/item/guid") == root.findtext("channel/item/link")
