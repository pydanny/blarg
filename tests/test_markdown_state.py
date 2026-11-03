import contextlib
import io
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from blarg.main import build_site, markdown


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a":
            self.anchors.append(values.get("href"))
        elif tag == "img":
            self.images.append(values.get("src"))


class MarkdownStateTests(unittest.TestCase):
    def setUp(self):
        # Isolate tests, without resetting between the builds under test.
        markdown.reset()
        self.addCleanup(markdown.reset)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write_page(self, source, name, body):
        source.mkdir(parents=True, exist_ok=True)
        (source / name).write_text(
            f"---\ntitle: {name}\n---\n{body}\n", encoding="utf-8"
        )

    def build(self, source, target):
        with contextlib.redirect_stdout(io.StringIO()):
            build_site(source, target)

    def read_page(self, target, article):
        html = (target / article / "index.html").read_text(encoding="utf-8")
        links = Links()
        links.feed(html)
        return html, links

    def test_unresolved_reference_stays_literal(self):
        source, target = self.root / "source", self.root / "site"
        self.write_page(source, "article.md", "[label][shared]")
        self.build(source, target)
        html, links = self.read_page(target, "article")
        self.assertEqual(links.anchors, [])
        self.assertIn("[label][shared]", html)

    def test_own_reference_definition_is_resolved(self):
        source, target = self.root / "source", self.root / "site"
        self.write_page(
            source,
            "article.md",
            "[label][shared]\n\n[shared]: https://example.invalid/own",
        )
        self.build(source, target)
        _, links = self.read_page(target, "article")
        self.assertEqual(links.anchors, ["https://example.invalid/own"])

    def test_articles_do_not_share_definitions_in_either_order(self):
        source, target = self.root / "source", self.root / "site"
        for name in ("alpha", "beta"):
            self.write_page(
                source,
                f"{name}.md",
                f"[A][alpha] [B][beta]\n\n[{name}]: https://example.invalid/{name}",
            )
        self.build(source, target)
        # Both articles reference both names, so either traversal order exposes
        # leaked state in the second article.
        actual = {
            name: self.read_page(target, name)[1].anchors for name in ("alpha", "beta")
        }
        self.assertEqual(
            actual,
            {
                "alpha": ["https://example.invalid/alpha"],
                "beta": ["https://example.invalid/beta"],
            },
        )

    def test_separate_builds_do_not_share_link_definitions(self):
        first, second = self.root / "first", self.root / "second"
        self.write_page(
            first,
            "article.md",
            "[label][shared]\n\n[shared]: https://example.invalid/first",
        )
        self.write_page(second, "article.md", "[label][shared]")
        self.build(first, self.root / "site-first")
        self.build(second, self.root / "site-second")
        html, links = self.read_page(self.root / "site-second", "article")
        self.assertEqual(links.anchors, [])
        self.assertIn("[label][shared]", html)

    def test_rebuild_drops_removed_definition(self):
        source, target = self.root / "source", self.root / "site"
        self.write_page(
            source,
            "article.md",
            "[label][shared]\n\n[shared]: https://example.invalid/removed",
        )
        self.build(source, target)
        self.write_page(source, "article.md", "[label][shared]")
        self.build(source, target)
        html, links = self.read_page(target, "article")
        self.assertEqual(links.anchors, [])
        self.assertIn("[label][shared]", html)

    def test_separate_builds_do_not_share_image_definitions(self):
        first, second = self.root / "first", self.root / "second"
        self.write_page(
            first,
            "article.md",
            "![logo][asset]\n\n[asset]: https://example.invalid/first.png",
        )
        self.write_page(second, "article.md", "![logo][asset]")
        self.build(first, self.root / "site-first")
        self.build(second, self.root / "site-second")
        html, links = self.read_page(self.root / "site-second", "article")
        self.assertEqual(links.images, [])
        self.assertIn("![logo][asset]", html)

    def test_configured_extensions_still_render_each_article(self):
        source, target = self.root / "source", self.root / "site"
        for name in ("alpha", "beta"):
            self.write_page(
                source,
                f"{name}.md",
                "~~removed~~\n\n| Name |\n| --- |\n| Example |",
            )
        self.build(source, target)
        for name in ("alpha", "beta"):
            with self.subTest(article=name):
                html, _ = self.read_page(target, name)
                self.assertIn("<del>removed</del>", html)
                self.assertIn("<table>", html)
                self.assertIn("<td>Example</td>", html)


if __name__ == "__main__":
    unittest.main()
