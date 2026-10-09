"""Cross-platform task runner for Khidki. No make required.

Usage: python tasks.py <command> [args...]
Run `python tasks.py help` to list commands.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS: dict[str, tuple[Callable[[list[str]], int], str]] = {}


def command(help_text: str) -> Callable[[Callable[[list[str]], int]], Callable[[list[str]], int]]:
    def register(fn: Callable[[list[str]], int]) -> Callable[[list[str]], int]:
        COMMANDS[fn.__name__.replace("_", "-")] = (fn, help_text)
        return fn

    return register


def run(cmd: list[str], cwd: Path = ROOT) -> int:
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=cwd)


def uv() -> str:
    exe = shutil.which("uv")
    if exe is None:
        sys.exit("uv is not installed. See https://docs.astral.sh/uv/ (macOS: brew install uv).")
    return exe


@command("Install Python dependencies (uv sync) and git hooks")
def setup(args: list[str]) -> int:
    print("Installing Python dependencies with uv...")
    rc = run([uv(), "sync", "--all-extras", "--all-groups"])
    if rc == 0 and (ROOT / ".git").exists():
        rc = run([uv(), "run", "pre-commit", "install"])
    return rc


@command("Run the Python test suite")
def test(args: list[str]) -> int:
    print("Running pytest...")
    return run([uv(), "run", "pytest", *args])


@command("Run ruff (all Python) and mypy (core/)")
def lint(args: list[str]) -> int:
    print("Linting with ruff, type-checking core/ with mypy...")
    rc = run([uv(), "run", "ruff", "check", "."])
    rc |= run([uv(), "run", "ruff", "format", "--check", "."])
    rc |= run([uv(), "run", "mypy"])
    return rc


@command("Auto-fix lint issues and format code")
def fmt(args: list[str]) -> int:
    print("Formatting with ruff...")
    rc = run([uv(), "run", "ruff", "check", "--fix", "."])
    rc |= run([uv(), "run", "ruff", "format", "."])
    return rc


def not_yet(phase: str) -> Callable[[list[str]], int]:
    def stub(args: list[str]) -> int:
        print(f"Not built yet: arrives in {phase} (see docs/SPEC.md §17.2).")
        return 1

    return stub


for _name, _phase, _help in [
    ("local", "Phase 2", "Run the whole app locally (no AWS account needed)"),
    ("sim", "Phase 2", "Run the classroom simulator against local or cloud"),
    ("bench", "Phase 7", "Run the policy benchmark over replay days"),
    ("cdk-synth", "Phase 4", "Synthesize the CDK app"),
    ("deploy", "Phase 4", "Deploy all stacks to AWS (ap-south-1)"),
    ("provision-device", "Phase 4", "Create an IoT thing and certificates for a room"),
    ("seed-demo", "Phase 4", "Seed the demo school and rooms"),
    ("synth-phrases", "Phase 5", "Pre-synthesize instruction phrases with Polly"),
    ("web-build", "Phase 5", "Build the web app"),
    ("web-deploy", "Phase 5", "Deploy the web app to Amplify"),
    ("demo-reset", "Phase 5", "Reset demo state between video takes"),
    ("arch-diagram", "Phase 8", "Render the architecture diagram"),
]:
    COMMANDS.setdefault(_name, (not_yet(_phase), _help))


@command("Cache real Delhi outdoor-air replay days from Open-Meteo")
def fetch_replay(args: list[str]) -> int:
    print("Fetching replay days (needs internet)...")
    return run([uv(), "run", "python", "scripts/fetch_replay.py", *args])


@command("List commands")
def help(args: list[str]) -> int:
    width = max(len(n) for n in COMMANDS)
    for name, (_, text) in sorted(COMMANDS.items()):
        print(f"  {name.ljust(width)}  {text}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in COMMANDS:
        if len(argv) >= 2:
            print(f"Unknown command: {argv[1]}\n")
        return COMMANDS["help"][0]([]) or (0 if len(argv) < 2 else 2)
    fn, _ = COMMANDS[argv[1]]
    return fn(argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
