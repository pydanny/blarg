import contextlib
import io
import os
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from blarg.main import build_site, markdown


class IndexLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []
        self.labels = []
        self.tags = []
        self.in_anchor = False

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "a":
            self.anchors.append(dict(attrs))
            self.labels.append("")
            self.in_anchor = True

    def handle_endtag(self, tag):
        if tag == "a":
            self.in_anchor = False

    def handle_data(self, data):
        if self.in_anchor:
            self.labels[-1] += data


class IndexLinkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source"
        self.target = self.root / "site"
        self.source.mkdir()
        markdown.reset()
        self.addCleanup(markdown.reset)

    def build_article(self, name):
        (self.source / f"{name}.md").write_text(
            "---\ntitle: Article\n---\n# Article body\n", encoding="utf-8"
        )
        with contextlib.redirect_stdout(io.StringIO()):
            build_site(self.source, self.target)
        parser = IndexLinks()
        parser.feed((self.target / "index.html").read_text(encoding="utf-8"))
        return parser

    def assert_article_link(self, parser, name, href):
        self.assertEqual(parser.anchors, [{"href": href}])
        self.assertEqual(parser.labels, [str(self.target / name)])
        # Follow the generated link as a URL, then resolve the decoded path.
        url = urlsplit(parser.anchors[0]["href"])
        self.assertEqual(
            (url.scheme, url.netloc, url.query, url.fragment), ("", "", "", "")
        )
        destination = self.target / unquote(url.path) / "index.html"
        self.assertIn("Article body</h1>", destination.read_text(encoding="utf-8"))

    def test_plain_article_keeps_existing_link_and_label(self):
        parser = self.build_article("ordinary-article_1")
        self.assert_article_link(parser, "ordinary-article_1", "ordinary-article_1")

    def test_fragment_character_is_part_of_the_article_path(self):
        parser = self.build_article("guide #1")
        self.assert_article_link(parser, "guide #1", "guide%20%231")

    def test_literal_percent_escape_is_not_decoded_as_a_space(self):
        parser = self.build_article("literal%20name")
        self.assert_article_link(parser, "literal%20name", "literal%2520name")

    def test_unicode_and_ampersand_remain_literal_filename_characters(self):
        parser = self.build_article("日本 & notes")
        self.assert_article_link(
            parser, "日本 & notes", "%E6%97%A5%E6%9C%AC%20%26%20notes"
        )

    @unittest.skipIf(os.name == "nt", "Windows disallows question marks in filenames")
    def test_query_character_is_part_of_the_article_path(self):
        parser = self.build_article("what?next")
        self.assert_article_link(parser, "what?next", "what%3Fnext")

    @unittest.skipIf(os.name == "nt", "Windows disallows colons in filenames")
    def test_colon_does_not_turn_relative_link_into_url_scheme(self):
        parser = self.build_article("topic:notes")
        self.assert_article_link(parser, "topic:notes", "topic%3Anotes")

    @unittest.skipIf(os.name == "nt", "Windows disallows double quotes in filenames")
    def test_filename_cannot_add_attributes_to_index_anchor(self):
        name = 'article" data-unexpected="yes'
        parser = self.build_article(name)
        self.assert_article_link(parser, name, "article%22%20data-unexpected%3D%22yes")

    @unittest.skipIf(os.name == "nt", "Windows disallows angle brackets in filenames")
    def test_filename_markup_is_rendered_as_link_text(self):
        parser = self.build_article("article<b>bold")
        self.assert_article_link(parser, "article<b>bold", "article%3Cb%3Ebold")
        self.assertNotIn("b", parser.tags)

    @unittest.skipIf(os.name == "nt", "Windows disallows angle brackets in filenames")
    def test_target_path_markup_is_rendered_as_link_text(self):
        self.target = self.root / "site<b>name"
        parser = self.build_article("ordinary")
        self.assert_article_link(parser, "ordinary", "ordinary")
        self.assertNotIn("b", parser.tags)


if __name__ == "__main__":
    unittest.main()
