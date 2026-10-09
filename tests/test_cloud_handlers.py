"""Lambda handlers end to end on moto: admin passcode, scenario start, device-key ingest, room view,
and Step Functions started when an instruction falls due."""

import importlib
import json
import os
from collections.abc import Iterator
from typing import Any

import boto3
import pytest
from moto import mock_aws

REGION = "ap-southeast-2"


class Ctx:
    function_name = "khidki-test"
    memory_limit_in_mb = 1769
    invoked_function_arn = "arn:aws:lambda:ap-southeast-2:123456789012:function:khidki-test"
    aws_request_id = "req-1"


def http(method: str, path: str, body: Any = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {"content-type": "application/json", **(headers or {})},
        "requestContext": {
            "http": {"method": method, "path": path, "sourceIp": "127.0.0.1"},
            "stage": "$default",
        },
        "body": json.dumps(body) if body is not None else None,
        "isBase64Encoded": False,
    }


@pytest.fixture
def cloud() -> Iterator[Any]:
    with mock_aws():
        os.environ.update(
            {
                "AWS_DEFAULT_REGION": REGION,
                "AWS_REGION": REGION,
                "KHIDKI_TABLE": "KhidkiT",
                "POWERTOOLS_METRICS_NAMESPACE": "Khidki",
                "POWERTOOLS_SERVICE_NAME": "khidki",
            }
        )
        from khidki_services.dynamo import create_table

        create_table("KhidkiT", boto3.resource("dynamodb", region_name=REGION))
        ssm = boto3.client("ssm", region_name=REGION)
        ssm.put_parameter(Name="/khidki/admin_key", Value="admin-pass", Type="String")
        ssm.put_parameter(Name="/khidki/device_key", Value="device-pass", Type="String")
        iam = boto3.client("iam", region_name=REGION)
        role = iam.create_role(RoleName="sfn", AssumeRolePolicyDocument="{}")["Role"]["Arn"]
        sm = boto3.client("stepfunctions", region_name=REGION).create_state_machine(
            name="NudgeSM",
            definition=json.dumps({"StartAt": "S", "States": {"S": {"Type": "Succeed"}}}),
            roleArn=role,
        )
        os.environ["KHIDKI_NUDGE_SM"] = sm["stateMachineArn"]
        from khidki_cloud import handlers, runtime

        importlib.reload(runtime)
        importlib.reload(handlers)
        yield handlers


def call(fn: Any, event: dict[str, Any]) -> tuple[int, Any]:
    r = fn(event, Ctx())
    return r["statusCode"], json.loads(r["body"]) if r.get("body") else None


def test_admin_and_device_keys_are_required(cloud: Any) -> None:
    code, _ = call(
        cloud.api, http("POST", "/v1/sim/control", {"action": "scenario", "scenario": "severe_morning"})
    )
    assert code == 401
    code, _ = call(cloud.ingest, http("POST", "/v1/ingest", {"room_id": "6B", "co2": 800}))
    assert code == 401


def test_scenario_ingest_and_room_view(cloud: Any) -> None:
    code, body = call(
        cloud.api,
        http(
            "POST",
            "/v1/sim/control",
            {"action": "scenario", "scenario": "severe_morning"},
            {"x-khidki-admin": "admin-pass"},
        ),
    )
    assert code == 200 and body["scenario"] == "severe_morning" and body["clock"]["simulated"]
    code, body = call(
        cloud.ingest,
        http(
            "POST",
            "/v1/ingest",
            {
                "readings": [
                    {"room_id": "6B", "co2": 1650, "pm25": 120},
                    {"room_id": "3A", "co2": 900, "pm25": 80},
                ]
            },
            {"x-khidki-device-key": "device-pass"},
        ),
    )
    assert code == 200 and body["stored"] == 2
    code, body = call(cloud.api, http("GET", "/v1/rooms/6B/now"))
    assert code == 200 and body["room_id"] == "6B" and body["simulated"]
    code, body = call(cloud.api, http("GET", "/v1/schools/dsv/today"))
    assert code == 200 and any("S2" in d["policy_ids"] for d in body["decisions"])
    code, body = call(
        cloud.api, http("POST", "/v1/agent/ask", {"room_id": "6B", "question": "PT bahar?", "lang": "hi"})
    )
    assert code == 200 and body["source"] == "template"
    code, _ = call(cloud.api, http("GET", "/v1/rooms/9Z/now"))
    assert code == 404


def test_nudge_task_steps(cloud: Any) -> None:
    call(
        cloud.api,
        http(
            "POST",
            "/v1/sim/control",
            {"action": "scenario", "scenario": "severe_morning"},
            {"x-khidki-admin": "admin-pass"},
        ),
    )
    with pytest.raises(KeyError):
        cloud.nudge_task({"mode": "verify", "nudge_id": "6B-1"}, Ctx())
