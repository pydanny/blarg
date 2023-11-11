import shutil
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from .mdconfig import md as markdown


env = Environment(
    loader=PackageLoader("blarg"),
    autoescape=select_autoescape()
)

template = env.get_template("theme.jinja2")


def build_site(source: Path, target: Path) -> None:
    try:
        shutil.rmtree(target)
    except FileNotFoundError:
        print("Target directory does not exist.")

    print(f"Building {target}")
    articles = []

    for page in source.rglob('*/*.md'):
        # print(page)
        content = page.read_text()
        frontmatter, _, text = content.partition('\n---\n')
        
        articles.append(target / Path(page.name).with_suffix(''))
        target_file = target / Path(page.name).with_suffix('') / Path('index.html')
        target_file.parent.mkdir(parents=True, exist_ok=True)        

        body = markdown.convert(text)
        target_file.write_text(template.render(body=body))

    # Index
    index = "<ul>"
    for article in articles:
        print(article)
        link = article.relative_to(target)
        index += f'\n<li><a href="{link}">{article}</a></li>'
    index += "</ul>"
    target_index = target / 'index.html'
    target_index.write_text(template.render(body=index, title="Index"))