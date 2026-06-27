# src/agents/agent_factory.py
# Author: Suresh D R | AI Product Developer & Technology Mentor

import json
import os
from openai import OpenAI
from src.utils.config import settings

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def load_prompt(name: str) -> str:
    with open(os.path.join(_PROMPTS_DIR, f"{name}.txt")) as f:
        return f.read()


GUARDRAILS_PROMPT   = load_prompt("guardrails")
CLASSIFIER_PROMPT   = load_prompt("classifier")
HYPOTHESIS_PROMPT   = load_prompt("hypothesis_generator")
RANKER_PROMPT       = load_prompt("significance_ranker")
ANOMALY_PROMPT      = load_prompt("anomaly_scanner")
SYNTHESIZER_PROMPT  = load_prompt("business_synthesizer")
FOLLOWUP_PROMPT     = load_prompt("followup_generator")


def call_mini_json(system_prompt: str, user_content: str) -> dict:
    """gpt-4o-mini — JSON response. Guardrails, Classifier, Anomaly Scanner."""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)


def call_full_json(system_prompt: str, user_content: str) -> dict:
    """gpt-4o — JSON response. Hypothesis Generator, Significance Ranker."""
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)


def call_mini_text(system_prompt: str, user_content: str) -> str:
    """gpt-4o-mini — free text. Business Synthesizer."""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content


def call_followup(question: str, answer: str) -> list:
    """Generate 3 follow-up question suggestions."""
    try:
        result = call_mini_json(
            FOLLOWUP_PROMPT,
            f"Question: {question}\nAnswer: {answer}"
        )
        return result.get("followup_questions", [])
    except Exception:
        return []
