"""Build the web app and publish it to the Amplify app created by CDK (manual deployment, no Git hookup).
/v1/* is proxied to the API by the app's rewrite rules, so the build needs no API URL.
Usage: python tasks.py web-deploy
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
REGION = "ap-southeast-2"


def main() -> int:
    outputs = json.loads((ROOT / "infra" / "outputs.json").read_text())["Khidki"]
    app_id, url = outputs["AmplifyAppId"], outputs["WebUrl"]
    print("Building the web app...")
    subprocess.run(["npx", "vite", "build"], cwd=ROOT / "web", check=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in (ROOT / "web" / "dist").rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(ROOT / "web" / "dist"))
    amp = boto3.client("amplify", region_name=REGION)
    dep = amp.create_deployment(appId=app_id, branchName="main")
    print(f"Uploading {len(buf.getvalue()) / 1e6:.1f} MB...")
    req = urllib.request.Request(
        dep["zipUploadUrl"], data=buf.getvalue(), method="PUT", headers={"Content-Type": "application/zip"}
    )
    urllib.request.urlopen(req, timeout=600).read()
    job = amp.start_deployment(appId=app_id, branchName="main", jobId=dep["jobId"])["jobSummary"]["jobId"]
    while True:
        status = amp.get_job(appId=app_id, branchName="main", jobId=job)["job"]["summary"]["status"]
        print("  deployment:", status)
        if status in ("SUCCEED", "FAILED", "CANCELLED"):
            break
        time.sleep(5)
    print(f"Live at {url}" if status == "SUCCEED" else "Deployment failed; see the Amplify console.")
    return 0 if status == "SUCCEED" else 1


if __name__ == "__main__":
    sys.exit(main())
