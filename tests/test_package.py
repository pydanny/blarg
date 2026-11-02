import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


class DistributionTests(unittest.TestCase):
    def test_wheel_can_build_html_and_markdown_outside_the_source_checkout(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "package"
            package.mkdir()
            for name in ["pyproject.toml", "README.md"]:
                shutil.copy2(project / name, package / name)
            shutil.copytree(
                project / "src/blarg",
                package / "src/blarg",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            build = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    "from setuptools.build_meta import build_wheel; build_wheel('dist')",
                ],
                cwd=package,
                text=True,
                capture_output=True,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            wheels = list((package / "dist").glob("*.whl"))
            self.assertEqual(len(wheels), 1)
            installed = root / "installed"
            with zipfile.ZipFile(wheels[0]) as wheel:
                wheel.extractall(installed)

            # Remove the source checkout from import paths: this must use the wheel.
            environment = os.environ.copy()
            paths = [
                path
                for path in environment.get("PYTHONPATH", "").split(os.pathsep)
                if path and Path(path).resolve() != project / "src"
            ]
            environment["PYTHONPATH"] = os.pathsep.join([str(installed), *paths])
            smoke = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    """from pathlib import Path
import blarg
from blarg.main import build_site

assert Path(blarg.__file__).resolve().is_relative_to(Path('installed').resolve())
source = Path('content')
source.mkdir()
(source / 'about.html').write_text('<h1>Hello {{ 6 * 7 }}</h1>', encoding='utf-8')
(source / 'article.md').write_text('---\\ntitle: Installed Markdown\\n---\\n# From wheel\\n', encoding='utf-8')
build_site(source, Path('site'))
assert Path('site/about.html').read_text(encoding='utf-8') == '<h1>Hello 42</h1>'
markdown = Path('site/article/index.html').read_text(encoding='utf-8')
assert '<title>Installed Markdown</title>' in markdown
assert 'From wheel</h1>' in markdown
assert Path('site/public/pygments.css').stat().st_size > 0
""",
                ],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
            )
            self.assertEqual(smoke.returncode, 0, smoke.stdout + smoke.stderr)


if __name__ == "__main__":
    unittest.main()
