# Meridian Retail Support-Draft Review Tool

A small command-line tool for a fictional classroom demo. It loads one support case
and the drafting policy, asks a Claude model for a draft reply, checks the reply's
structure, and prints the result for a human to review.

The tool drafts only. It never sends messages, approves refunds, or changes records.

## Files

- `app.py` - the command-line tool
- `policy.md` - drafting policy (P1-P4)
- `cases.json` - three synthetic cases (C1, C2, C3)
- `demo_outputs.json` - labelled, prerecorded synthetic results for `--offline-demo`
- `setup_env.py` - writes a project-only `.env` with your app key and model
- `test_app.py`, `test_setup_env.py` - tests; they never call an external API

## Setup

With [uv](https://docs.astral.sh/uv/):

```bash
uv venv .venv
uv pip install -r requirements.txt
uv run --no-project python setup_env.py
```

Run any command below with `uv run --no-project` in front, or activate the
environment first with `source .venv/bin/activate`.

`setup_env.py` asks for the key with hidden input and asks for the model
(default `claude-haiku-4-5-20251001`). It writes `.env` in this folder with
permissions 600 and never prints the key. It overwrites any existing `.env`.

The app reads only `APP_ANTHROPIC_API_KEY` and `APP_ANTHROPIC_MODEL`. It does not
read or set `ANTHROPIC_API_KEY`. See `.env.example` for the format.

## Usage

```bash
python app.py --case C1                     # live model call
python app.py --case C1 --offline-demo      # prerecorded synthetic result, no API call
python app.py --case C1 --simulate-timeout  # unavailable state, no API call
```

Output has three sections: `SUPPLIED FACTS`, `SUPPLIED POLICY`, and
`DRAFT RESULT FOR HUMAN REVIEW`.

The draft result has four fields:

- `draft_reply` - text
- `evidence_refs` - policy IDs (P1-P4)
- `missing_information` - case field names
- `review_status` - `READY_FOR_HUMAN_REVIEW`, `NEEDS_INFORMATION`, or `BLOCKED`

## Safety behaviour

- **Missing delivery date:** if the case has no `delivery_date`, the app does not
  call the model. It returns a fixed `NEEDS_INFORMATION` result citing P2 and P4.
- **Failures:** a provider error, timeout, missing key, or invalid model output
  shows `review_status: UNAVAILABLE`, an empty draft, and a manual fallback message.
  No traceback and no stale draft is shown.
- **Client settings:** 20-second timeout, no retries.
- **Validation limits:** the app checks field names and types only. Correct
  structure does not prove correct content. A human must review every draft.

## Tests

```bash
python -m pytest -q
```

The tests use fake model functions and never call an external API.
