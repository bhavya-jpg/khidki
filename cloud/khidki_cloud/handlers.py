"""Lambda entry points.

- api:        every /v1 route the web app uses (Powertools router), Cedar-checked admin actions
- ingest:     POST /v1/ingest from a sensor node or the simulator (device key), then ticks that room
- planner:    EventBridge Scheduler, 06:00 Asia/Kolkata: the day's decisions and every room's plan
- nudge_task: the steps of the NudgeSM state machine (await the tap, timeout, verify from CO₂)
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

import boto3
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver, CORSConfig
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, NotFoundError, UnauthorizedError

from khidki_agent.answer import ask as agent_ask
from khidki_agent.tools import Tools
from khidki_cloud import runtime
from khidki_core.policy import POLICIES
from khidki_data.openmeteo import ATTRIBUTION

logger = Logger(service="khidki")
metrics = Metrics(namespace="Khidki", service="khidki")
VERSION = "0.3.0"
BUCKET = os.environ.get("KHIDKI_BUCKET", "")
ALLOWED_ORIGINS = [o for o in os.environ.get("KHIDKI_ORIGINS", "http://localhost:5173").split(",") if o]

app = APIGatewayHttpResolver(
    cors=CORSConfig(
        allow_origin=ALLOWED_ORIGINS[0],
        extra_origins=ALLOWED_ORIGINS[1:],
        allow_headers=["Content-Type", "x-khidki-admin"],
    )
)


def _secret_ok(header: str, param: str) -> bool:
    given = app.current_event.headers.get(header, "")
    try:
        expected = runtime.ssm_param(param)
    except Exception:
        logger.exception("could not read %s", param)
        return False
    return bool(given) and hmac.compare_digest(given, expected)


def _body() -> dict[str, Any]:
    body = app.current_event.json_body
    if not isinstance(body, dict):
        raise BadRequestError("Expected a JSON object")
    return body


@app.get("/v1/health")
def health() -> dict[str, Any]:
    e = runtime.engine(metrics)
    item = runtime.clock_item() or {}
    return {
        "ok": True,
        "version": VERSION,
        "mode": "cloud",
        "region": runtime.REGION,
        "clock": e.clock_view(),
        "scenario": item.get("scenario"),
        "attribution": ATTRIBUTION,
    }


@app.get("/v1/rooms/<room_id>/now")
def room_now(room_id: str) -> dict[str, Any]:
    try:
        return runtime.engine(metrics).room_now(room_id)
    except KeyError as exc:
        raise NotFoundError(f"No room {room_id}") from exc


@app.get("/v1/rooms/<room_id>/plan")
def room_plan(room_id: str) -> dict[str, Any]:
    plan = runtime.engine(metrics).plan_view(room_id)
    if plan is None:
        raise NotFoundError("No plan yet. Plans start at 07:00.")
    return plan


@app.post("/v1/rooms/<room_id>/replan")
def replan(room_id: str) -> dict[str, Any]:
    e = runtime.engine(metrics)
    e.replan(room_id, reason="requested")
    return e.plan_view(room_id) or {}


@app.post("/v1/nudges/<nudge_id>/ack")
def ack(nudge_id: str) -> dict[str, Any]:
    body = _body()
    try:
        n = runtime.engine(metrics).ack(nudge_id, str(body.get("result")), body.get("reason"))
    except KeyError as exc:
        raise NotFoundError("That instruction has already finished.") from exc
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    return {"nudge_id": n["nudge_id"], "state": n["state"]}


@app.get("/v1/schools/<school_id>/today")
def school_today(school_id: str) -> dict[str, Any]:
    e = runtime.engine(metrics)
    if school_id != e.school.school_id:
        raise NotFoundError(f"No school {school_id}")
    return e.school_today()


@app.post("/v1/schools/<school_id>/override")
def override(school_id: str) -> dict[str, Any]:
    """The demo principal signs in with the admin passcode; Cedar still decides (A2/A3) and it is logged."""
    if not _secret_ok("x-khidki-admin", "/khidki/admin_key"):
        raise UnauthorizedError("Principal passcode required")
    body = _body()
    try:
        return runtime.engine(metrics).override(
            str(body.get("key")), bool(body.get("outdoor")), str(body.get("reason", "")), user_id="principal"
        )
    except KeyError as exc:
        raise NotFoundError("No such decision today") from exc
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc


@app.get("/v1/schools/<school_id>/audit")
def audit(school_id: str) -> list[dict[str, Any]]:
    return runtime.engine(metrics).audit()


@app.post("/v1/agent/ask")
def agent() -> dict[str, Any]:
    body = _body()
    room_id, question, lang = (
        str(body.get("room_id", "")),
        str(body.get("question", ""))[:400],
        body.get("lang", "hi"),
    )
    e = runtime.engine(metrics)
    try:
        e.room_cfg(room_id)
    except KeyError as exc:
        raise NotFoundError(f"No room {room_id}") from exc
    llm = None
    if os.environ.get("KHIDKI_BEDROCK") == "1":
        from khidki_agent.bedrock import make_llm

        llm = make_llm()
    a = agent_ask(Tools(e), room_id, question, "en" if lang == "en" else "hi", llm=llm)
    metrics.add_metric(
        name="AgentTemplateAnswers" if a.source == "template" else "AgentLlmAnswers", unit="Count", value=1
    )
    return {
        "answer": a.answer,
        "lang": a.lang,
        "source": a.source,
        "numbers_verified": a.numbers_verified,
        "tools_used": a.tools_used,
        "tool_outputs": a.tool_outputs,
        "note": a.note,
    }


@app.get("/v1/policies")
def policies() -> dict[str, Any]:
    return {pid: {"en": p.en, "hi": p.hi, "source": p.source} for pid, p in POLICIES.items()}


@app.get("/v1/rooms/<room_id>/audio")
def audio(room_id: str) -> dict[str, Any]:
    """The current instruction in Hindi, spoken by Polly (Kajal), cached in S3 by a hash of the text."""
    view = runtime.engine(metrics).room_now(room_id)
    text = view["card"]["text"]["hi"]
    key = f"audio/{hashlib.sha256(('kajal|hi-IN|' + text).encode()).hexdigest()[:24]}.mp3"
    s3 = boto3.client("s3", region_name=runtime.REGION)
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
    except s3.exceptions.ClientError:
        speech = boto3.client("polly", region_name=runtime.REGION).synthesize_speech(
            Engine="neural", VoiceId="Kajal", LanguageCode="hi-IN", OutputFormat="mp3", Text=text
        )
        s3.put_object(Bucket=BUCKET, Key=key, Body=speech["AudioStream"].read(), ContentType="audio/mpeg")
        metrics.add_metric(name="PollySyntheses", unit="Count", value=1)
    url = s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=3600)
    return {"text": text, "url": url, "voice": "Kajal (Amazon Polly, neural)"}


@app.get("/v1/sim/scenarios")
def list_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "name": s["name"],
            "description": s["description"],
            "date": s["date"],
            "teacher": s["teacher"]["mode"],
        }
        for s in runtime.scenarios().values()
    ]


@app.post("/v1/sim/control")
def sim_control() -> dict[str, Any]:
    if not _secret_ok("x-khidki-admin", "/khidki/admin_key"):
        raise UnauthorizedError("Admin passcode required")
    body = _body()
    action = body.get("action")
    if action in ("scenario", "reset"):
        name = body.get("scenario") or (runtime.clock_item() or {}).get("scenario") or "severe_morning"
        if name not in runtime.scenarios():
            raise NotFoundError(f"No scenario {name}")
        item = runtime.reset_demo(str(name), body.get("speed"))
    elif action == "speed" and body.get("speed"):
        item = runtime.update_clock(speed=float(body["speed"]))
    elif action in ("pause", "resume"):
        item = runtime.update_clock(paused=action == "pause")
    else:
        raise BadRequestError("action must be scenario, reset, speed, pause or resume")
    return {"scenario": item["scenario"], "clock": runtime.engine(metrics).clock_view()}


@logger.inject_lambda_context
@metrics.log_metrics
def api(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return app.resolve(event, context)


# ── ingest ──────────────────────────────────────────────────────────────────────────────────────────
ingest_app = APIGatewayHttpResolver()


@ingest_app.post("/v1/ingest")
def ingest_route() -> dict[str, Any]:
    given = ingest_app.current_event.headers.get("x-khidki-device-key", "")
    if not given or not hmac.compare_digest(given, runtime.ssm_param("/khidki/device_key")):
        raise UnauthorizedError("Device key required")
    body = ingest_app.current_event.json_body
    readings = body.get("readings", [body]) if isinstance(body, dict) else []
    e = runtime.engine(metrics)
    rooms: set[str] = set()
    for r in readings[:50]:
        rid = str(r.get("room_id", ""))
        try:
            e.room_cfg(rid)
        except KeyError as exc:
            raise NotFoundError(f"No room {rid}") from exc
        co2 = float(r["co2"])
        if not 0 < co2 < 10000:
            raise BadRequestError("co2 out of range")
        e.ingest(
            rid,
            {
                "ts": r.get("ts"),
                "co2": co2,
                "pm25": r.get("pm25"),
                "simulated": bool(r.get("simulated", True)),
            },
        )
        rooms.add(rid)
    e.tick(room_ids=sorted(rooms))
    metrics.add_metric(name="ReadingsIngested", unit="Count", value=len(readings))
    return {"stored": len(readings), "clock": e.clock_view()}


@logger.inject_lambda_context
@metrics.log_metrics
def ingest(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return ingest_app.resolve(event, context)


# ── planner (EventBridge Scheduler) ─────────────────────────────────────────────────────────────────
@logger.inject_lambda_context
@metrics.log_metrics
def planner(event: dict[str, Any], context: Any) -> dict[str, Any]:
    e = runtime.engine(metrics)
    day = e.day()
    made = {}
    for r in e.school.rooms:
        plan = e.replan(r.room_id, reason="06:00 plan")
        made[r.room_id] = len(plan.instructions) if plan else 0
    metrics.add_metric(name="PlansMade", unit="Count", value=len(made))
    logger.info(
        "morning plan",
        extra={
            "date": day["date"],
            "grap": day["grap_stage"],
            "instructions": made,
            "decisions": [(d["key"], d["outdoor"], d["policy_ids"]) for d in day["decisions"]],
        },
    )
    return {"date": day["date"], "instructions": made}


# ── NudgeSM steps ───────────────────────────────────────────────────────────────────────────────────
OUTCOME_METRIC = {
    "verified": "NudgesVerified",
    "verified_silent": "NudgesVerified",
    "partial": "NudgesPartial",
    "not_followed": "NudgesNotFollowed",
    "not_possible": "NudgesNotPossible",
}


@logger.inject_lambda_context
@metrics.log_metrics
def nudge_task(event: dict[str, Any], context: Any) -> dict[str, Any]:
    e = runtime.engine(metrics)
    mode, nid = event["mode"], event["nudge_id"]
    if mode == "await_ack":
        view = e.sf_await_ack(nid, event["token"])
    elif mode == "timeout":
        view = e.sf_timeout(nid)
    elif mode == "verify":
        view = e.sf_verify(nid)
        if view["status"] == "follow_up":
            metrics.add_metric(name="NudgesFollowUp", unit="Count", value=1)
        elif view["outcome"] in OUTCOME_METRIC:
            metrics.add_metric(name=OUTCOME_METRIC[view["outcome"]], unit="Count", value=1)
    else:
        raise ValueError(f"unknown mode {mode}")
    logger.info(
        "nudge step",
        extra={
            "mode": mode,
            **{k: view.get(k) for k in ("nudge_id", "status", "outcome")},
            "evidence": view.get("evidence"),
        },
    )
    return view


__all__ = ["api", "ingest", "nudge_task", "planner"]
