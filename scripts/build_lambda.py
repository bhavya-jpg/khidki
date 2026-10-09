"""Build the Lambda assets for CDK: build/layer (Linux x86_64 wheels for Python 3.12) and build/lambda (our
packages + scenarios.json). Works offline from the uv cache.
Usage: python scripts/build_lambda.py
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
LAYER_REQS = [
    "numpy==2.2.6",  # the newest manylinux wheel available offline; the code uses stable numpy 2 APIs
    "pydantic==2.13.5",
    "pydantic-core==2.46.5",
    "cedarpy==4.12.1",
    "aws-lambda-powertools==3.35.0",
    "typing-extensions==4.16.0",
    "annotated-types==0.8.0",
    "typing-inspection==0.4.4",
    "jmespath==1.1.0",
]
PACKAGES = [
    "core/khidki_core",
    "data/khidki_data",
    "services/khidki_services",
    "agent/khidki_agent",
    "cloud/khidki_cloud",
]


def build_layer() -> None:
    target = BUILD / "layer" / "python"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    cmd = [
        "uv",
        "pip",
        "install",
        "--offline",
        "--no-deps",
        "--target",
        str(target),
        "--python-platform",
        "x86_64-manylinux2014",
        "--python-version",
        "3.12",
        "--only-binary",
        ":all:",
        *LAYER_REQS,
    ]
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)
    for junk in target.rglob("__pycache__"):
        shutil.rmtree(junk, ignore_errors=True)
    for tests in target.glob("numpy/*/tests"):
        shutil.rmtree(tests, ignore_errors=True)


def build_code() -> None:
    out = BUILD / "lambda"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for pkg in PACKAGES:
        src = ROOT / pkg
        skip = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
        shutil.copytree(src, out / src.name, ignore=skip)
    sys.path.insert(0, str(ROOT / "sim"))
    from khidki_sim import scenario as sc

    data = [dataclasses.asdict(sc.load(n)) for n in sc.list_scenarios()]
    (out / "khidki_cloud" / "scenarios.json").write_text(json.dumps(data))


def main() -> int:
    build_layer()
    build_code()
    size = sum(f.stat().st_size for f in (BUILD / "layer").rglob("*") if f.is_file()) / 1e6
    print(f"layer: {size:.0f} MB unzipped (limit 250 MB with the code)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
