import importlib.metadata
from pathlib import Path
from subprocess import check_call

import typer
from rich import print

from .main import build_site


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
def serve2(site: Path = Path("site"), port: int = 8000):
    """Serve the site"""
    from .server import server

    server(site=site, port=port)


@app.command()
def version():
    """Get the blarg version"""
    print(f"[bold green]{importlib.metadata.version('blarg')}[/bold green]")


if __name__ == "__main__":
    app()
