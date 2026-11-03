import importlib.util
import os
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


BASE = Path(__file__).resolve().parents[1] / "src/blarg/cli.py"


class Typer:
    def command(self):
        return lambda function: function


def load_cli():
    package = types.ModuleType("blarg")
    package.__path__ = []
    main = types.ModuleType("blarg.main")
    main.build_site = lambda *a, **kw: None
    typer = types.ModuleType("typer")
    typer.Typer = Typer
    rich = types.ModuleType("rich")
    rich.print = print
    with patch.dict(
        sys.modules,
        {"blarg": package, "blarg.main": main, "typer": typer, "rich": rich},
    ):
        spec = importlib.util.spec_from_file_location("blarg.cli", BASE)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    return m


class TestServe(unittest.TestCase):
    def test_invokes_current_interpreter_with_argument_list(self):
        m = load_cli()
        site = Path("a path with spaces")
        calls = []
        m.check_call = lambda args: calls.append(args)
        m.serve(site)
        self.assertEqual(
            calls, [[sys.executable, "-m", "http.server", "8000", "-d", site]]
        )

    def test_serve_child_command_works_when_path_empty(self):
        m = load_cli()
        results = []

        def safe_probe(args):
            env = dict(os.environ, PATH="")
            results.append(
                subprocess.run(
                    args[:3] + ["--help"],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=5,
                ).returncode
            )

        m.check_call = safe_probe
        m.serve(Path("."))
        self.assertEqual(results, [0])

    def test_current_executable_available_when_path_empty(self):
        env = dict(os.environ, PATH="")
        r = subprocess.run(
            [sys.executable, "-m", "http.server", "--help"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
