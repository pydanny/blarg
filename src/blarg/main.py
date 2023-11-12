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


def build_site(source: Path, target: Path, template: Path = "default.html") -> None:
    # Cleanup build directory
    try:
        shutil.rmtree(target)
    except FileNotFoundError:
        print("Target directory does not exist.")

    template = template_env.get_template(template)

    print(f"[bold green]Building {target}")
    articles = []

    pages = list(source.rglob("*/*.md"))
    page_build_count = 0

    for page in track(pages, description=f"Attempting to build {len(pages)} pages"):
        if "node_modules" in page.parts:
            continue
        # print(page)
        content = page.read_text()
        frontmatter, _, text = content.partition("\n---\n")

        articles.append(target / Path(page.name).with_suffix(""))
        target_file = target / Path(page.name).with_suffix("") / Path("index.html")
        target_file.parent.mkdir(parents=True, exist_ok=True)

        body = markdown.convert(text)
        # try:
        try:
            target_file.write_text(
                template.render(body=Markup(body), meta=yaml.safe_load(frontmatter))
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
        template.render(body=Markup(index), meta={"title": "Index"})
    )

    print(f"[bold green]Done building {page_build_count} files[/bold green]")
