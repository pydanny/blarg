from pathlib import Path
from subprocess import check_call
import importlib.metadata

import typer

from .main import build_site

from rich import print

app = typer.Typer()


@app.command()
def build(source: Path = Path("."), target: Path = Path("site")):
    """Build the site"""
    build_site(source, target)


@app.command()
def serve(site: Path = Path("site")):
    """Serve the site"""
    check_call(["python", "-m", "http.server", "8000", "-d", site])


@app.command()
def version():
    """Get the blarg version"""
    print(f"[bold green]{importlib.metadata.version('blarg')}[/bold green]")


if __name__ == "__main__":
    app()
