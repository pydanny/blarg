import os
import shutil
from pathlib import Path

import yaml
from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    select_autoescape,
)
from markupsafe import Markup
from rich import print
from rich.progress import track

from .mdconfig import md as markdown
from .mdconfig import render_pygments_css


# Load templates
template_env = Environment(
    loader=ChoiceLoader([PackageLoader("blarg"), FileSystemLoader("templates")]),
    autoescape=select_autoescape(),
)


def _content_pages(source: Path, target: Path) -> tuple[list[Path], list[Path]]:
    """Discover content without following links or walking generated/templates files."""
    markdown_pages, html_pages = [], []
    for directory, directories, filenames in os.walk(source, followlinks=False):
        directory = Path(directory)
        directories[:] = sorted(
            name
            for name in directories
            if not name.startswith(".")
            and name not in {"templates", "node_modules"}
            and not (directory / name).is_symlink()
            and (directory / name).resolve() != target.resolve()
        )
        for name in sorted(filenames):
            page = directory / name
            if name.startswith(".") or page.is_symlink():
                continue
            if page.suffix == ".md":
                markdown_pages.append(page)
            elif page.suffix == ".html":
                html_pages.append(page)
    return markdown_pages, html_pages


def _check_destinations(destinations: list[Path]) -> None:
    """Reject file/file and file/directory collisions before deleting any output."""
    seen: set[Path] = set()
    for destination in destinations:
        if any(
            destination == other
            or destination in other.parents
            or other in destination.parents
            for other in seen
        ):
            raise ValueError(f"Conflicting output path: {destination}")
        seen.add(destination)


def build_site(source: Path, target: Path, template: Path = "default.html") -> None:
    source, target = Path(source), Path(target)
    if not source.is_dir():
        raise ValueError(f"Source is not a directory: {source}")
    if target.is_symlink() or source.resolve().is_relative_to(target.resolve()):
        raise ValueError("Target must not be a symlink, the source, or its ancestor")

    pages, html_pages = _content_pages(source, target)
    html_destinations = [page.relative_to(source) for page in html_pages]
    _check_destinations(
        [Path("index.html"), Path("public/pygments.css")]
        + [Path(page.stem) / "index.html" for page in pages]
        + html_destinations
    )
    # Render before cleanup so a malformed HTML template cannot erase the last build.
    rendered_html = [
        template_env.from_string(page.read_text(encoding="utf-8")).render()
        for page in html_pages
    ]
    template = template_env.get_template(template)

    # Cleanup build directory
    try:
        shutil.rmtree(target)
    except FileNotFoundError:
        print("Target directory does not exist.")

    print(f"[bold green]Building {target}")

    articles = [target / Path(x.name).with_suffix("") for x in pages]
    page_build_count = 0

    for page in track(pages, description=f"Building {len(pages)} pages"):
        content = page.read_text()
        frontmatter, _, text = content.partition("\n---\n")

        target_file = target / Path(page.name).with_suffix("") / Path("index.html")
        target_file.parent.mkdir(parents=True, exist_ok=True)

        body = markdown.convert(text)
        # try:
        try:
            target_file.write_text(
                template.render(
                    body=Markup(body), frontmatter=yaml.safe_load(frontmatter)
                )
            )
        except yaml.parser.ParserError:
            print(f"[bold red]Error parsing frontmatter for {page}[/bold red]")
            continue
        except yaml.scanner.ScannerError:
            print(f"[bold red]Error scanning frontmatter for {page}[/bold red]")
            continue
        except yaml.composer.ComposerError:
            print(f"[bold red]Error composing frontmatter for {page}[/bold red]")
            continue
        page_build_count += 1

    for destination, content in zip(html_destinations, rendered_html):
        target_file = target / destination
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(content, encoding="utf-8")
        page_build_count += 1

    # Pygments colors
    target_css = target / "public" / "pygments.css"
    target_css.parent.mkdir(parents=True, exist_ok=True)
    target_css.write_text(render_pygments_css())

    # Index
    index = "<ul>"
    for article in articles:
        link = article.relative_to(target)
        index += f'\n<li><a href="{link}">{article}</a></li>'
    index += "</ul>"
    target_index = target / "index.html"

    target_index.write_text(
        template.render(body=Markup(index), frontmatter={"title": "Index"})
    )

    print(f"[bold green]Done building {page_build_count} files[/bold green]")
