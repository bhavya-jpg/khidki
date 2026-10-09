"""One Converse call per route to find a Bedrock model this account can actually use.

Tries Nova 2 Lite via the global inference profile first (from our home region, then us-east-1), then
in-region Nova Lite. Prints which worked. Exit code 0 if any did.
Usage: python scripts/smoke_bedrock.py
"""

from __future__ import annotations

import os
import sys
import time

import boto3

PROMPT = "Reply with one Hindi word meaning 'window'."
HOME = os.environ.get("KHIDKI_REGION", "ap-southeast-2")
ROUTES = [
    ("global.amazon.nova-2-lite-v1:0", HOME),
    ("global.amazon.nova-2-lite-v1:0", "us-east-1"),
    ("us.amazon.nova-2-lite-v1:0", "us-east-1"),
    ("apac.amazon.nova-lite-v1:0", HOME),
    ("amazon.nova-lite-v1:0", "us-east-1"),
]


def main() -> int:
    ok = False
    for model, region in ROUTES:
        client = boto3.client("bedrock-runtime", region_name=region)
        t0 = time.perf_counter()
        try:
            r = client.converse(
                modelId=model,
                messages=[{"role": "user", "content": [{"text": PROMPT}]}],
                inferenceConfig={"maxTokens": 20, "temperature": 0.2},
            )
            text = r["output"]["message"]["content"][0]["text"].strip()
            print(f"OK    {model:34s} @ {region:15s} {time.perf_counter() - t0:4.1f}s  -> {text}")
            ok = True
        except Exception as exc:  # report every route, don't stop at the first failure
            print(f"FAIL  {model:34s} @ {region:15s} {str(exc)[:110]}")
    if not ok:
        print(
            "\nNo route worked. 'Operation not allowed' is an account security restriction: open an AWS "
            "Support case (Account and billing) and ask for Amazon Bedrock access. Ask Khidki falls back "
            "to templates."
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
