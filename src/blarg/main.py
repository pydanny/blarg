import shutil
from pathlib import Path

import markdown

def build_site(source: Path, target: Path) -> None:
    try:
        shutil.rmtree(target)
    except FileNotFoundError:
        print("Target directory does not exist.")

    print(f"Building {target}")
    articles = []

    for page in source.rglob('*/*.md'):
        # print(page)
        text = page.read_text()
        frontmatter, content = text.split('\n---\n')       
        
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