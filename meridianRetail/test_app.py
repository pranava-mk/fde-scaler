import json
from types import SimpleNamespace

import pytest

import app

REAL_CALL_MODEL = app.call_model

VALID = {
    "draft_reply": "Sorry about the zip. A human will review your return request.",
    "evidence_refs": ["P1", "P4"],
    "missing_information": [],
    "review_status": "READY_FOR_HUMAN_REVIEW",
}


@pytest.fixture(autouse=True)
def no_external(monkeypatch):
    def boom(prompt):
        raise AssertionError("real call_model must not be used in tests")

    monkeypatch.setattr(app, "call_model", boom)
    monkeypatch.delenv("APP_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("APP_ANTHROPIC_MODEL", raising=False)


def no_call(prompt):
    raise AssertionError("model must not be called")


def test_input_files():
    cases = json.loads(app.CASES_PATH.read_text(encoding="utf-8"))
    assert set(cases) >= {"C1", "C2", "C3"}
    fields = {"case_id", "order_id", "product", "customer_question",
              "delivery_date", "issue_status", "issue_details"}
    for key in ("C1", "C2", "C3"):
        assert set(cases[key]) == fields
        assert cases[key]["case_id"] == key
    assert cases["C2"]["delivery_date"] is None
    policy = app.load_policy()
    for pid in ("P1", "P2", "P3", "P4"):
        assert pid in policy


def test_successful_c1(capsys):
    calls = []

    def fake(prompt):
        calls.append(prompt)
        return json.dumps(VALID)

    assert app.run("C1", model_fn=fake) == VALID
    out = capsys.readouterr().out
    for header in ("=== SUPPLIED FACTS ===", "=== SUPPLIED POLICY ===",
                   "=== DRAFT RESULT FOR HUMAN REVIEW ==="):
        assert header in out
    assert VALID["draft_reply"] in out
    assert "Structure check passed" in out
    assert "Draft only. Nothing has been sent, no refund approved, no record changed." in out
    assert len(calls) == 1
    assert "MR-1042" in calls[0]
    assert app.load_policy() in calls[0]


def test_fenced_json_accepted():
    text = "```json\n" + json.dumps(VALID) + "\n```"
    assert app.parse_model_output(text) == VALID
    assert app.parse_model_output("```\n" + json.dumps(VALID) + "\n```") == VALID


def _bad(**changes):
    data = dict(VALID)
    data.update(changes)
    return json.dumps(data)


def _without_key():
    data = dict(VALID)
    del data["draft_reply"]
    return json.dumps(data)


@pytest.mark.parametrize("bad", [
    "not json at all",
    _without_key(),
    _bad(extra="x"),
    _bad(evidence_refs="P1"),
    _bad(evidence_refs=["P9"]),
    _bad(review_status="APPROVED"),
    _bad(draft_reply=""),
])
def test_invalid_outputs(bad, capsys):
    result = app.run("C1", model_fn=lambda p: bad)
    out = capsys.readouterr().out
    assert result == app.unavailable_result()
    assert app.MANUAL_FALLBACK_MESSAGE in out
    assert "Traceback" not in out


@pytest.mark.parametrize("exc", [TimeoutError("secret-detail-1"), RuntimeError("secret-detail-2")])
def test_provider_error(exc, capsys):
    def fake(prompt):
        raise exc

    result = app.run("C1", model_fn=fake)
    out = capsys.readouterr().out
    assert result == app.unavailable_result()
    assert type(exc).__name__ in out
    assert "secret-detail" not in out
    assert "Traceback" not in out
    assert app.MANUAL_FALLBACK_MESSAGE in out


def test_simulate_timeout(capsys):
    result = app.run("C1", simulate_timeout=True, model_fn=no_call)
    out = capsys.readouterr().out
    assert result["draft_reply"] == ""
    assert result["review_status"] == "UNAVAILABLE"
    assert app.MANUAL_FALLBACK_MESSAGE in out


@pytest.mark.parametrize("case_id", ["C1", "C2", "C3"])
def test_offline_demo(case_id, capsys):
    result = app.run(case_id, offline_demo=True, model_fn=no_call)
    out = capsys.readouterr().out
    label, _ = app.load_demo_output(case_id)
    assert "No model API was called" in out
    assert label in out
    assert app.validate_result(result) == result


def test_demo_outputs_file():
    demo = json.loads(app.DEMO_PATH.read_text(encoding="utf-8"))
    for case_id in ("C1", "C2", "C3"):
        assert demo[case_id]["label"]
        app.validate_result(demo[case_id]["result"])
    assert demo["C2"]["result"] == app.MISSING_DELIVERY_DATE_RESULT
    assert demo["C3"]["result"]["review_status"] == "BLOCKED"


def test_missing_delivery_date(capsys):
    calls = []

    def fake(prompt):
        calls.append(prompt)
        raise AssertionError("model must not be called")

    assert app.run("C2", model_fn=fake) == app.MISSING_DELIVERY_DATE_RESULT
    assert calls == []


def test_missing_result_is_copy():
    r = app.run("C2", model_fn=no_call)
    r["evidence_refs"].append("P1")
    assert app.MISSING_DELIVERY_DATE_RESULT["evidence_refs"] == ["P2", "P4"]


@pytest.mark.parametrize("case,expected", [
    ({"delivery_date": None}, False),
    ({"delivery_date": ""}, False),
    ({"delivery_date": "  "}, False),
    ({}, False),
    ({"delivery_date": "2026-09-12"}, True),
])
def test_has_delivery_date(case, expected):
    assert app.has_delivery_date(case) is expected


def _fake_anthropic(monkeypatch, captured):
    class FakeMessages:
        def create(self, **kwargs):
            captured["create"] = kwargs
            return SimpleNamespace(content=[
                SimpleNamespace(type="text", text="{"),
                SimpleNamespace(type="other", text="IGNORED"),
                SimpleNamespace(type="text", text="}"),
            ])

    class FakeAnthropic:
        def __init__(self, **kwargs):
            captured["init"] = kwargs
            self.messages = FakeMessages()

    monkeypatch.setattr(app, "Anthropic", FakeAnthropic)


def test_call_model_wiring(monkeypatch):
    captured = {}
    _fake_anthropic(monkeypatch, captured)
    monkeypatch.setenv("APP_ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "should-not-be-used")
    assert REAL_CALL_MODEL("hello") == "{}"
    assert captured["init"] == {"api_key": "test-key", "timeout": 20, "max_retries": 0}
    assert captured["create"]["model"] == app.DEFAULT_MODEL
    assert captured["create"]["max_tokens"] == 1024
    assert captured["create"]["messages"] == [{"role": "user", "content": "hello"}]


def test_call_model_model_override(monkeypatch):
    captured = {}
    _fake_anthropic(monkeypatch, captured)
    monkeypatch.setenv("APP_ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("APP_ANTHROPIC_MODEL", "custom-model")
    REAL_CALL_MODEL("hi")
    assert captured["create"]["model"] == "custom-model"


def test_call_model_missing_key():
    with pytest.raises(RuntimeError):
        REAL_CALL_MODEL("hi")


def test_main_unknown_case():
    with pytest.raises(SystemExit):
        app.main(["--case", "C9"])


def test_main_mutually_exclusive():
    with pytest.raises(SystemExit):
        app.main(["--case", "C1", "--simulate-timeout", "--offline-demo"])


def test_main_offline_demo():
    assert app.main(["--case", "C1", "--offline-demo"]) == 0
