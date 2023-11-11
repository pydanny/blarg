from subprocess import check_call
from pathlib import Path

import typer

from .main import build_site


app = typer.Typer()


@app.command()
def build(source: Path = Path('.'), target: Path = Path('site')):
    """Build the site"""
    build_site(source, target)


@app.command()
def serve(site: Path = Path('site')):
    """Serve the site"""
    check_call(['python', '-m', 'http.server', '8000', '-d', site])


if __name__ == "__main__":
    app()