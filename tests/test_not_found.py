import contextlib
import io
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from blarg.main import build_site, markdown


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.in_title = False
        self.title = ""
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        if tag == "a":
            self.links.append(dict(attrs).get("href"))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


class NotFoundTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.target = self.root / "site"
        markdown.reset()
        self.addCleanup(markdown.reset)

    def article(self, name, title="Article"):
        (self.source / name).write_text(
            f"---\ntitle: {title}\n---\n# Custom body\n", encoding="utf-8"
        )

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build_site(self.source, self.target)

    def default_page(self):
        path = self.target / "404.html"
        self.assertTrue(path.is_file(), "Build must generate the default 404.html")
        return path.read_text(encoding="utf-8")

    def test_empty_site_generates_titled_default_page(self):
        self.build()
        html = self.default_page()
        self.assertEqual(Page(html).title, "404 - Blarg")
        self.assertIn("<h1>404 - Blarg</h1>", html)
        self.assertIn('href="/public/pygments.css"', html)

    def test_default_illustration_is_accessible_self_contained_svg(self):
        self.build()
        html = self.default_page()
        self.assertIn("<svg", html)
        svg = ElementTree.fromstring(
            html[html.index("<svg") : html.index("</svg>") + 6]
        )
        self.assertEqual(svg.attrib.get("role"), "img")
        self.assertTrue(svg.attrib.get("aria-label"))
        self.assertTrue(svg.attrib.get("viewBox"))
        self.assertGreater(len(list(svg)), 1)
        for node in svg.iter():
            self.assertNotIn(
                node.tag.split("}")[-1], ["script", "image", "use", "foreignObject"]
            )
            for attribute in node.attrib:
                self.assertNotIn(attribute.split("}")[-1], ["href", "src"])

    def test_generated_page_does_not_enter_article_index(self):
        self.article("guide.md")
        self.build()
        self.default_page()
        self.assertEqual(
            Page((self.target / "index.html").read_text()).links, ["guide"]
        )
        self.assertIn("Custom body", (self.target / "guide/index.html").read_text())

    def test_repeated_build_regenerates_default_page(self):
        self.build()
        original = self.default_page()
        (self.target / "404.html").write_text("stale output")
        self.article("next.md")
        self.build()
        self.assertEqual(self.default_page(), original)
        self.assertEqual(Page((self.target / "index.html").read_text()).links, ["next"])

    def test_markdown_404_keeps_existing_mapping_and_content(self):
        self.article("404.md", "My missing page")
        self.build()
        self.assertFalse((self.target / "404.html").exists())
        custom = (self.target / "404/index.html").read_text()
        self.assertEqual(Page(custom).title, "My missing page")
        self.assertIn("Custom body", custom)
        self.assertEqual(Page((self.target / "index.html").read_text()).links, ["404"])


if __name__ == "__main__":
    unittest.main()
