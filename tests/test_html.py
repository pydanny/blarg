import contextlib
import os
import tempfile
import unittest
from pathlib import Path

from jinja2 import TemplateNotFound, TemplateSyntaxError

from blarg.main import build_site


class HTMLBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.target = self.root / "site"
        previous = Path.cwd()
        os.chdir(self.source)
        self.addCleanup(os.chdir, previous)

    def write(self, name, content):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def build(self, target=None):
        with open(os.devnull, "w") as output, contextlib.redirect_stdout(output):
            build_site(self.source, target or self.target)

    def preserve_target_on_error(self, error=ValueError):
        self.target.mkdir()
        sentinel = self.target / "keep.txt"
        sentinel.write_text("existing output", encoding="utf-8")
        with self.assertRaises(error):
            self.build()
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "existing output")

    def test_renders_complete_html_at_its_relative_path(self):
        self.write(
            "docs/hello.html",
            "<h1>你好 {{ 6 * 7 }}</h1>{% for n in [1, 2] %}<p>{{ n }}</p>{% endfor %}",
        )
        self.build()
        output = self.target / "docs/hello.html"
        self.assertTrue(output.is_file(), "HTML source must produce a rendered page")
        self.assertEqual(
            output.read_text(encoding="utf-8"), "<h1>你好 42</h1><p>1</p><p>2</p>"
        )

    def test_html_uses_existing_autoescaping(self):
        self.write("safe.html", '<p>{{ "<script>" }}</p>')
        self.build()
        output = self.target / "safe.html"
        self.assertTrue(output.is_file())
        self.assertEqual(output.read_text(), "<p>&lt;script&gt;</p>")

    def test_local_includes_are_templates_not_output_pages(self):
        self.write("templates/part.html", "<strong>{{ 21 * 2 }}</strong>")
        self.write("about.html", '<main>{% include "part.html" %}</main>')
        self.build()
        output = self.target / "about.html"
        self.assertTrue(output.is_file())
        self.assertEqual(output.read_text(), "<main><strong>42</strong></main>")
        self.assertFalse((self.target / "templates").exists())

    def test_markdown_keeps_its_existing_layout_and_flat_output_path(self):
        self.write(
            "nested/article.md", "---\ntitle: Original article\n---\n# Hello Markdown\n"
        )
        self.build()
        text = (self.target / "article/index.html").read_text()
        self.assertIn("<title>Original article</title>", text)
        self.assertIn("Hello Markdown</h1>", text)
        self.assertFalse((self.target / "nested/article/index.html").exists())

    def test_html_and_markdown_with_same_stem_have_distinct_destinations(self):
        self.write("article.html", "<p>HTML {{ 42 }}</p>")
        self.write("article.md", "---\ntitle: Markdown\n---\nMarkdown body\n")
        self.build()
        self.assertTrue((self.target / "article.html").is_file())
        self.assertIn("Markdown body", (self.target / "article/index.html").read_text())

    def test_generated_index_and_css_are_preserved(self):
        self.write("article.md", "---\ntitle: Article\n---\nBody\n")
        self.build()
        self.assertIn('<a href="article">', (self.target / "index.html").read_text())
        self.assertGreater((self.target / "public/pygments.css").stat().st_size, 0)

    def test_index_collision_is_rejected_before_cleanup(self):
        self.write("index.html", "Custom index")
        self.preserve_target_on_error()

    def test_markdown_html_collision_is_rejected_before_cleanup(self):
        self.write("article.md", "---\ntitle: Article\n---\nBody\n")
        self.write("article/index.html", "Colliding HTML")
        self.preserve_target_on_error()

    def test_output_file_directory_collision_is_rejected_before_cleanup(self):
        self.write("article.html.md", "---\ntitle: Article\n---\nBody\n")
        self.write("article.html", "Conflicting file")
        self.preserve_target_on_error()

    def test_generated_css_parent_collision_is_rejected_before_cleanup(self):
        self.write("public/pygments.css/nested.html", "Conflicting directory")
        self.preserve_target_on_error()

    def test_excluded_directories_are_not_rendered(self):
        for directory in [
            "templates",
            "nested/templates",
            "node_modules",
            ".hidden",
            ".git",
        ]:
            self.write(f"{directory}/skip.html", "{% invalid %}")
            self.write(f"{directory}/skip.md", "---\ntitle: Excluded\n---\nNo\n")
        self.write(".hidden.html", "{% invalid %}")
        self.write("visible.html", "Visible")
        self.build()
        self.assertTrue((self.target / "visible.html").is_file())
        self.assertFalse((self.target / "skip/index.html").exists())
        self.assertFalse((self.target / ".hidden.html").exists())
        self.assertNotIn("skip", (self.target / "index.html").read_text())

    def test_output_subtree_is_not_rediscovered(self):
        self.target = self.source / "generated"
        self.write("generated/stale.html", "{% invalid %}")
        self.write("generated/stale.md", "---\ntitle: Stale\n---\nNo\n")
        self.write("visible.html", "Current {{ 42 }}")
        self.build()
        self.assertTrue((self.target / "visible.html").is_file())
        self.assertFalse((self.target / "generated").exists())
        self.assertFalse((self.target / "stale/index.html").exists())

    def test_outside_symlink_content_is_not_rendered(self):
        outside = self.root / "outside.html"
        outside.write_text("{% invalid %}")
        try:
            (self.source / "linked.html").symlink_to(outside)
            (self.source / "linked_dir").symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation is unavailable")
        self.write("visible.html", "Visible")
        self.build()
        self.assertTrue((self.target / "visible.html").is_file())
        self.assertFalse((self.target / "linked.html").exists())
        self.assertFalse((self.target / "linked_dir").exists())
        self.assertEqual(outside.read_text(), "{% invalid %}")

    def test_invalid_html_template_preserves_existing_output(self):
        self.write("broken.html", "{% invalid %}")
        self.preserve_target_on_error(TemplateSyntaxError)

    def test_missing_html_include_preserves_existing_output(self):
        self.write("broken.html", '{% include "does-not-exist.html" %}')
        self.preserve_target_on_error(TemplateNotFound)

    def test_target_equal_to_source_is_rejected_without_deleting_inputs(self):
        page = self.write("keep.html", "Keep")
        with self.assertRaises(ValueError):
            self.build(self.source)
        self.assertEqual(page.read_text(), "Keep")

    def test_target_ancestor_of_source_is_rejected_without_deleting_inputs(self):
        page = self.write("keep.html", "Keep")
        with self.assertRaises(ValueError):
            self.build(self.root)
        self.assertEqual(page.read_text(), "Keep")

    def test_missing_source_preserves_existing_output(self):
        self.source = self.root / "missing"
        self.preserve_target_on_error()

    def test_duplicate_markdown_destinations_are_rejected_before_cleanup(self):
        self.write("one/article.md", "---\ntitle: One\n---\nFirst\n")
        self.write("two/article.md", "---\ntitle: Two\n---\nSecond\n")
        self.preserve_target_on_error()

    def test_symlink_target_preserves_link_and_destination(self):
        external = self.root / "external"
        external.mkdir()
        sentinel = external / "keep.txt"
        sentinel.write_text("Keep")
        try:
            self.target.symlink_to(external, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation is unavailable")
        with self.assertRaises(ValueError):
            self.build()
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(sentinel.read_text(), "Keep")


if __name__ == "__main__":
    unittest.main()
