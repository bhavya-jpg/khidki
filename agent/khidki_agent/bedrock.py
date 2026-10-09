"""The LLM side: a Strands agent on Amazon Bedrock that rephrases tool results for a teacher.

The tools are already called deterministically (answer.gather); the agent receives their JSON and writes a
short answer. It has no tools that change anything. Output goes through the number-fidelity guard.
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any

SYSTEM_PROMPT = """You are Khidki's assistant for a school teacher in Delhi.
Rules:
- Answer in the language requested (Hindi in Devanagari, or English). At most 80 words.
- Use ONLY facts and numbers from the TOOL RESULTS. Never invent a number, time or policy.
- Copy numbers exactly as they appear. Do not do arithmetic.
- You cannot change the plan or open windows. If asked, say the teacher can tap the buttons on the screen.
- If a policy (like S2) decided something, name it and its reason.
- Not medical advice. For health problems, suggest seeing a doctor.
- Calm, kind, practical. No alarmist language."""

DEFAULT_MODEL = "global.amazon.nova-2-lite-v1:0"
TIMEOUT_S = 8.0


def make_llm(model_id: str | None = None, region: str | None = None) -> Any:
    from strands import Agent
    from strands.models import BedrockModel

    model = BedrockModel(
        model_id=model_id or os.environ.get("KHIDKI_BEDROCK_MODEL", DEFAULT_MODEL),
        region_name=region
        or os.environ.get("KHIDKI_BEDROCK_REGION", os.environ.get("AWS_REGION", "ap-south-1")),
        temperature=0.2,
        max_tokens=600,
    )
    pool = ThreadPoolExecutor(max_workers=2)

    def llm(question: str, lang: str, calls: list[tuple[str, dict[str, Any]]]) -> str:
        agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, callback_handler=None)
        results = "\n".join(f"{name}: {json.dumps(out, ensure_ascii=False)}" for name, out in calls)
        prompt = (
            f"Language: {'Hindi' if lang == 'hi' else 'English'}\nTeacher's question: {question}\n\n"
            f"TOOL RESULTS:\n{results}"
        )
        fut = pool.submit(lambda: str(agent(prompt)))
        try:
            return fut.result(timeout=TIMEOUT_S)
        except FutureTimeout as exc:
            raise TimeoutError("Bedrock took longer than 8 s") from exc

    return llm
