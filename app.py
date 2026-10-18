"""Meridian Retail support-draft review tool. Drafts only; a human reviews."""
import argparse
import json
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
CASES_PATH = BASE_DIR / "cases.json"
POLICY_PATH = BASE_DIR / "policy.md"
DEMO_PATH = BASE_DIR / "demo_outputs.json"

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
POLICY_IDS = {"P1", "P2", "P3", "P4"}
ALLOWED_STATUSES = {"READY_FOR_HUMAN_REVIEW", "NEEDS_INFORMATION", "BLOCKED"}
REQUIRED_FIELDS = ("draft_reply", "evidence_refs", "missing_information", "review_status")
MANUAL_FALLBACK_MESSAGE = "Draft unavailable. Handle this case manually using policy.md."
MISSING_DELIVERY_DATE_RESULT = {
    "draft_reply": (
        "Before Meridian Retail can assess whether this case falls within the "
        "two-day damage-reporting rule, please provide the delivery date. "
        "A human support agent will review the request once that information "
        "is available."
    ),
    "evidence_refs": ["P2", "P4"],
    "missing_information": ["delivery_date"],
    "review_status": "NEEDS_INFORMATION",
}


def _copy_result(result):
    return {
        "draft_reply": result["draft_reply"],
        "evidence_refs": list(result["evidence_refs"]),
        "missing_information": list(result["missing_information"]),
        "review_status": result["review_status"],
    }


def load_case(case_id):
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if case_id not in cases:
        raise KeyError(f"Unknown case: {case_id}")
    return cases[case_id]


def load_policy():
    return POLICY_PATH.read_text(encoding="utf-8")


def build_prompt(case, policy):
    return (
        "You draft customer support replies for Meridian Retail. A human agent "
        "will review your draft before anything is sent.\n"
        "Use ONLY the supplied case facts and policy below. Do not invent facts.\n"
        "The draft is for human review only. It must not approve refunds, "
        "promise outcomes, or say an open issue is resolved.\n\n"
        "CASE FACTS (JSON):\n" + json.dumps(case, indent=2) + "\n\n"
        "POLICY:\n" + policy + "\n\n"
        "Return ONLY a JSON object with exactly these 4 keys and no other text:\n"
        '- "draft_reply": string, the draft reply to the customer\n'
        '- "evidence_refs": list of policy IDs used, e.g. ["P1"]\n'
        '- "missing_information": list of case field names that are missing\n'
        '- "review_status": one of "READY_FOR_HUMAN_REVIEW", '
        '"NEEDS_INFORMATION", "BLOCKED"\n'
    )


def call_model(prompt):
    key = os.environ.get("APP_ANTHROPIC_API_KEY")
    if not key or not key.strip():
        raise RuntimeError("APP_ANTHROPIC_API_KEY is not set")
    model = os.environ.get("APP_ANTHROPIC_MODEL") or DEFAULT_MODEL
    client = Anthropic(api_key=key, timeout=20, max_retries=0)
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in response.content if b.type == "text")


def validate_result(data):
    if not isinstance(data, dict) or set(data) != set(REQUIRED_FIELDS):
        raise ValueError("result must be an object with exactly the required fields")
    reply = data["draft_reply"]
    if not isinstance(reply, str) or not reply.strip():
        raise ValueError("draft_reply must be a non-empty string")
    refs = data["evidence_refs"]
    if not isinstance(refs, list) or not all(isinstance(r, str) and r in POLICY_IDS for r in refs):
        raise ValueError("evidence_refs must be a list of known policy IDs")
    missing = data["missing_information"]
    if not isinstance(missing, list) or not all(isinstance(m, str) for m in missing):
        raise ValueError("missing_information must be a list of strings")
    if data["review_status"] not in ALLOWED_STATUSES:
        raise ValueError("review_status not allowed")
    return {
        "draft_reply": reply,
        "evidence_refs": list(refs),
        "missing_information": list(missing),
        "review_status": data["review_status"],
    }


def parse_model_output(text):
    text = text.strip()
    if text.startswith("```") and text.endswith("```") and len(text) >= 6:
        text = text[3:-3]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return validate_result(json.loads(text))


def unavailable_result():
    return {
        "draft_reply": "",
        "evidence_refs": [],
        "missing_information": [],
        "review_status": "UNAVAILABLE",
    }


def has_delivery_date(case):
    value = case.get("delivery_date")
    return isinstance(value, str) and bool(value.strip())


def load_demo_output(case_id):
    entry = json.loads(DEMO_PATH.read_text(encoding="utf-8"))[case_id]
    return entry["label"], validate_result(entry["result"])


def run(case_id, *, simulate_timeout=False, offline_demo=False, model_fn=call_model):
    case = load_case(case_id)
    policy = load_policy()
    print("=== SUPPLIED FACTS ===")
    for field, value in case.items():
        print(f"{field}: {value}")
    print("=== SUPPLIED POLICY ===")
    print(policy)
    print("=== DRAFT RESULT FOR HUMAN REVIEW ===")

    if simulate_timeout:
        result = unavailable_result()
        print("MODEL UNAVAILABLE (simulated timeout). No model API was called.")
    elif offline_demo:
        label, result = load_demo_output(case_id)
        print("OFFLINE DEMO: No model API was called.")
        print("Source: " + label)
    elif not has_delivery_date(case):
        result = _copy_result(MISSING_DELIVERY_DATE_RESULT)
        print("Delivery date missing: deterministic result. No model API was called.")
    else:
        try:
            result = parse_model_output(model_fn(build_prompt(case, policy)))
        except Exception as exc:
            result = unavailable_result()
            print("MODEL UNAVAILABLE: " + type(exc).__name__)

    for field in REQUIRED_FIELDS:
        print(f"{field}: {result[field]}")
    if result["review_status"] == "UNAVAILABLE":
        print(MANUAL_FALLBACK_MESSAGE)
    else:
        print(
            "Structure check passed. Structure does not prove the content is "
            "correct; a human must review it."
        )
    print("Draft only. Nothing has been sent, no refund approved, no record changed.")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Meridian Retail support-draft review tool")
    parser.add_argument("--case", required=True, choices=["C1", "C2", "C3"])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--simulate-timeout", action="store_true")
    group.add_argument("--offline-demo", action="store_true")
    args = parser.parse_args(argv)
    load_dotenv(BASE_DIR / ".env")
    run(args.case, simulate_timeout=args.simulate_timeout, offline_demo=args.offline_demo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
