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
    ("sim", "Phase 2", "Run the classroom simulator against local or cloud"),
    ("provision-device", "Phase 4", "Create an IoT thing and certificates for a room"),
    ("seed-demo", "Phase 4", "Seed the demo school and rooms"),
    ("synth-phrases", "Phase 5", "Pre-synthesize instruction phrases with Polly"),
    ("web-build", "Phase 5", "Build the web app"),
    ("web-deploy", "Phase 5", "Deploy the web app to Amplify"),
    ("demo-reset", "Phase 5", "Reset demo state between video takes"),
    ("arch-diagram", "Phase 8", "Render the architecture diagram"),
]:
    COMMANDS.setdefault(_name, (not_yet(_phase), _help))


@command("Run Khidki locally: API + simulator on :8000 and the web app on :5173 (no AWS account needed)")
def local(args: list[str]) -> int:
    import os

    scenario = args[0] if args else "severe_morning"
    env = {**os.environ, "KHIDKI_SCENARIO": scenario}
    print(f"Starting local mode with scenario '{scenario}'. API: http://localhost:8000/v1/health")
    api = subprocess.Popen(
        [uv(), "run", "uvicorn", "khidki_local.app:app", "--port", "8000"], cwd=ROOT, env=env
    )
    web = None
    if (ROOT / "web" / "package.json").exists():
        if not (ROOT / "web" / "node_modules").exists():
            run(["npm", "install"], cwd=ROOT / "web")
        print("Web app: http://localhost:5173/teacher/6B")
        web = subprocess.Popen(["npm", "run", "dev"], cwd=ROOT / "web")
    try:
        return api.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        for proc in (api, web):
            if proc and proc.poll() is None:
                proc.terminate()


@command("Run the 48-day benchmark (Khidki vs baselines) and write docs/benchmark.md + chart")
def bench(args: list[str]) -> int:
    print("Running the benchmark on every replay day (a few minutes)...")
    rc = run([uv(), "run", "python", "bench/run_benchmark.py", *args])
    return rc or run([uv(), "run", "python", "bench/report.py"])


REGION = "ap-southeast-2"  # the account's home region (docs/SCOPE.md)


def _env_keys() -> dict[str, str]:
    """Demo device and admin keys, generated once into .env (gitignored)."""
    import os
    import secrets

    env_file = ROOT / ".env"
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    values = dict(line.split("=", 1) for line in lines if "=" in line and not line.startswith("#"))
    changed = False
    for key in ("KHIDKI_DEVICE_KEY", "KHIDKI_ADMIN_KEY"):
        if not values.get(key):
            values[key] = secrets.token_urlsafe(18)
            lines.append(f"{key}={values[key]}")
            changed = True
    if changed:
        env_file.write_text("\n".join(lines) + "\n")
        print("Generated demo keys in .env")
    return {
        **os.environ,
        "KHIDKI_DEVICE_KEY": values["KHIDKI_DEVICE_KEY"],
        "KHIDKI_ADMIN_KEY": values["KHIDKI_ADMIN_KEY"],
        "KHIDKI_REGION": REGION,
        "AWS_REGION": REGION,
        "CDK_DEFAULT_REGION": REGION,
    }


@command("Build Lambda assets and synthesize the CDK app")
def cdk_synth(args: list[str]) -> int:
    rc = run([uv(), "run", "--offline", "python", "scripts/build_lambda.py"])
    if rc:
        return rc
    env = _env_keys()
    print("$ cdk synth (infra/)")
    return subprocess.call(["cdk", "synth", "--quiet"], cwd=ROOT / "infra", env=env)


@command("Deploy everything to AWS (ap-southeast-2): build assets, bootstrap once, cdk deploy")
def deploy(args: list[str]) -> int:
    rc = run([uv(), "run", "--offline", "python", "scripts/build_lambda.py"])
    if rc:
        return rc
    env = _env_keys()
    account = subprocess.run(
        ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()
    if not account:
        print("AWS credentials not found. Run `aws configure` first.")
        return 1
    env["CDK_DEFAULT_ACCOUNT"] = account
    print(f"Bootstrapping CDK in {account}/{REGION} (no-op if already done)...")
    rc = subprocess.call(["cdk", "bootstrap", f"aws://{account}/{REGION}"], cwd=ROOT / "infra", env=env)
    if rc:
        return rc
    print("Deploying the Khidki stack...")
    return subprocess.call(
        [
            "cdk",
            "deploy",
            "--require-approval",
            "never",
            "--outputs-file",
            str(ROOT / "infra" / "outputs.json"),
            *args,
        ],
        cwd=ROOT / "infra",
        env=env,
    )


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
