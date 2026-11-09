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
    

    pages = list(source.rglob("*.md"))
    articles = [target / Path(x.name).with_suffix("") for x in pages]
    page_build_count = 0

    for page in track(pages, description=f"Building {len(pages)} pages"):
        if "node_modules" in page.parts:
            continue
        content = page.read_text()
        frontmatter, _, text = content.partition("\n---\n")

        target_file = target / Path(page.name).with_suffix("") / Path("index.html")
        target_file.parent.mkdir(parents=True, exist_ok=True)

        body = markdown.convert(text)
        # try:
        try:
            target_file.write_text(
                template.render(body=Markup(body), frontmatter=yaml.safe_load(frontmatter))
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
        template.render(body=Markup(index), frontmatter={"title": "Index"})
    )

    if not (target / "404.html").exists() and not (target / "404/index.html").exists():
        not_found = Markup(
            "<p>This page wandered off. Our robot is looking for it.</p>"
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 180" '
            'width="240" height="180" role="img" aria-label="A puzzled robot looking for a lost page">'
            '<rect x="60" y="50" width="120" height="95" rx="20" fill="#8ac6d1" stroke="#243746" stroke-width="4"/>'
            '<path d="M120 50V25M90 145v20M150 145v20" stroke="#243746" stroke-width="6"/>'
            '<circle cx="120" cy="20" r="8" fill="#eaa84b"/>'
            '<circle cx="95" cy="85" r="10" fill="#243746"/>'
            '<circle cx="145" cy="85" r="10" fill="#243746"/>'
            '<path d="M98 120q22-18 44 0" fill="none" stroke="#243746" stroke-width="5"/>'
            '<text x="195" y="45" font-size="36" fill="#243746">?</text>'
            "</svg>"
        )
        (target / "404.html").write_text(
            template.render(body=not_found, frontmatter={"title": "404 - Blarg"}),
            encoding="utf-8",
        )

    print(f"[bold green]Done building {page_build_count} files[/bold green]")
