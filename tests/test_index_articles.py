import contextlib
import io
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from blarg.main import build_site, markdown


class ArticleLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.append(dict(attrs)["href"])


class IndexArticleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.target = self.root / "site"
        markdown.reset()
        self.addCleanup(markdown.reset)

    def write_article(self, name, frontmatter="title: Article"):
        page = self.source / name
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(f"---\n{frontmatter}\n---\n# Article body\n", encoding="utf-8")

    def build(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            build_site(self.source, self.target)
        links = ArticleLinks()
        links.feed((self.target / "index.html").read_text(encoding="utf-8"))
        return links.hrefs, output.getvalue()

    def assert_articles_exist(self, hrefs):
        for href in hrefs:
            with self.subTest(href=href):
                article = self.target / href / "index.html"
                self.assertTrue(article.is_file(), f"Index links to missing {article}")
                self.assertIn("Article body</h1>", article.read_text(encoding="utf-8"))

    def test_caught_yaml_errors_are_not_linked(self):
        self.write_article("good.md")
        errors = [
            ("title: [broken", "parsing"),
            ("\ttitle: broken", "scanning"),
            ("title: *undefined", "composing"),
        ]
        for frontmatter, diagnostic in errors:
            with self.subTest(diagnostic=diagnostic):
                self.write_article("bad.md", frontmatter)
                hrefs, output = self.build()
                self.assertIn(f"Error {diagnostic} frontmatter", output)
                self.assertIn("Done building 1 files", output)
                self.assertFalse((self.target / "bad/index.html").exists())
                self.assertEqual(hrefs, ["good"])
                self.assert_articles_exist(hrefs)

    def test_all_failed_articles_leave_an_empty_index(self):
        self.write_article("bad.md", "title: [broken")
        hrefs, output = self.build()
        self.assertIn("Done building 0 files", output)
        self.assertEqual(hrefs, [])
        self.assertGreater((self.target / "public/pygments.css").stat().st_size, 0)

    def test_nested_sources_link_only_their_built_articles(self):
        self.write_article("posts/good.md")
        self.write_article("posts/bad.md", "title: *undefined")
        hrefs, _ = self.build()
        self.assertEqual(hrefs, ["good"])
        self.assert_articles_exist(hrefs)

    def test_rebuild_removes_failed_article_and_keeps_success_order(self):
        names = ["a/last.md", "b/middle.md", "c/first.md"]
        for name in names:
            self.write_article(name)
        # Fix discovery order independently of filesystem enumeration. The index
        # must preserve that order, not just agree with a previous build's order.
        pages = [self.source / name for name in names]
        with patch.object(Path, "rglob", return_value=pages):
            original, _ = self.build()
            self.assertEqual(original, ["last", "middle", "first"])
            self.assert_articles_exist(original)

            self.write_article("b/middle.md", "title: [broken")
            rebuilt, _ = self.build()
        self.assertFalse((self.target / "middle/index.html").exists())
        self.assertEqual(rebuilt, ["last", "first"])
        self.assert_articles_exist(rebuilt)

    def test_corrected_article_is_linked_on_the_next_build(self):
        self.write_article("article.md", "title: [broken")
        hrefs, _ = self.build()
        self.assertEqual(hrefs, [])

        self.write_article("article.md")
        hrefs, _ = self.build()
        self.assertEqual(hrefs, ["article"])
        self.assert_articles_exist(hrefs)

    def test_skipped_node_modules_article_is_not_linked(self):
        self.write_article("good.md")
        self.write_article("node_modules/dependency/ignored.md")
        hrefs, _ = self.build()
        self.assertFalse((self.target / "ignored/index.html").exists())
        self.assertEqual(hrefs, ["good"])
        self.assert_articles_exist(hrefs)

    def test_empty_source_still_builds_index_and_styles(self):
        hrefs, output = self.build()
        self.assertEqual(hrefs, [])
        self.assertIn("Done building 0 files", output)
        self.assertGreater((self.target / "public/pygments.css").stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
