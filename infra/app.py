"""CDK app. Region: ap-southeast-2, this account's home region (see docs/SCOPE.md).

Keys and the owner's alert email come from the environment (python tasks.py deploy reads .env)."""

import os

import aws_cdk as cdk
from stacks.khidki_stack import KhidkiStack

app = cdk.App()
KhidkiStack(
    app,
    "Khidki",
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("KHIDKI_REGION", "ap-southeast-2"),
    ),
    device_key=os.environ.get("KHIDKI_DEVICE_KEY", "change-me-device"),
    admin_key=os.environ.get("KHIDKI_ADMIN_KEY", "change-me-admin"),
    alert_email=os.environ.get("KHIDKI_ALERT_EMAIL", ""),
    description="Khidki: plan, nudge and verify classroom ventilation (Environmental Hacks 2026)",
)
app.synth()
