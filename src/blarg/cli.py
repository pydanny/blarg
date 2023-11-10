from pathlib import Path
import shutil

import markdown
import typer
from rich import print


app = typer.Typer()


def segment_page(page: Path) -> dict[str, str]:
    """Split a page into its frontmatter and content."""

    text = page.read_text()
    contents = text.split('\n---\n')
    return {'frontmatter': contents[0], 'content': contents[1]}


@app.command()
def serve(source: Path, target: Path):
    try:
        shutil.rmtree(target)
    except FileNotFoundError:
        print("Target directory does not exist.")

    print(f"Building {target}")
    articles = []

    for page in source.rglob('*/*.md'):
        # print(page)
        try:
            segmented_page = segment_page(page)
        except IndexError:
            continue
        frontmatter = segmented_page['frontmatter']
        content = segmented_page['content']
        
        articles.append(target / Path(page.name).with_suffix(''))
        target_file = target / Path(page.name).with_suffix('') / Path('index.html')
        target_file.parent.mkdir(parents=True, exist_ok=True)        

        html = markdown.markdown(content, extensions=['pymdownx.magiclink'])
        target_file.write_text(html)

    # Index
    index = "<ul>"
    for article in articles:
        print(article)
        link = article.relative_to(target)
        index += f'\n<li><a href="{link}">{article}</a></li>'
    index += "</ul>"
    target_index = target / 'index.html'
    target_index.write_text(index)

if __name__ == "__main__":
    app()