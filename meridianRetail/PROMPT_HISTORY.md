# Prompt History

The prompts used to build this project with Claude Code, in order.
Prompts 1-3 were provided by the course and are copied verbatim.
The rest are follow-up requests made during the session.

## 1. Course prompt: create the input files

> Create exactly two input files for a fictional Meridian Retail classroom demo. Do not create the application yet and do not add extra features.
>
> 1. Create policy.md with exactly this content:
>
> # Meridian Retail Support Drafting Policy
>
> P1. Damage reported within two days of delivery can be referred for human return review. This does not mean a refund has been approved.
>
> P2. The delivery date is required to apply the two-day rule. If it is missing, ask for it.
>
> P3. If the issue record says open, the draft must not say the issue is resolved.
>
> P4. This assistant drafts for human review only. It cannot approve refunds, send messages, or change records.
>
> 2. Create cases.json as one JSON object with three keys: C1, C2, and C3.
>
> C1 fields:
> case_id C1; order_id MR-1042; product Jacket; customer_question "The jacket arrived yesterday and the zip is broken. Can I return it?"; delivery_date "2026-09-12"; issue_status open; issue_details "Zip broken on arrival".
>
> C2 fields:
> case_id C2; order_id MR-1088; product Jacket; customer_question "The jacket has a broken zip. Can I return it?"; delivery_date null; issue_status open; issue_details "Zip broken; delivery date missing".
>
> C3 fields:
> case_id C3; order_id MR-1126; product Shoes; customer_question "Please confirm that my issue is resolved."; delivery_date "2026-09-10"; issue_status open; issue_details "Replacement request is still under review".
>
> After creating only those two files, validate cases.json with Python and report whether it is valid JSON.

**Result:** created `policy.md` and `cases.json`; `cases.json` validated as JSON.

## 2. Course prompt: build the review tool (plan first)

This prompt was sent twice; Claude Code showed a file plan and waited for approval both times.

> Build the smallest useful Meridian Retail support-draft review tool in this folder. First explain your file plan and wait for my approval before writing files. Do not add a web UI, database, RAG system, login flow, agent framework, or production integration.Use the existing policy.md and cases.json. Create:- app.py- README.md- requirements.txt- setup_env.py- .env.example- .gitignore- demo_outputs.json- test_app.py and test_setup_env.pyBehaviour required in app.py:1. Run as: python app.py --case C1. Accept C1, C2, or C3.2. Load the chosen case from cases.json and the policy from policy.md relative to app.py.3. Print three clearly labelled sections: SUPPLIED FACTS, SUPPLIED POLICY, and DRAFT RESULT FOR HUMAN REVIEW.4. Call the Anthropic Python SDK. Read the application key only from APP_ANTHROPIC_API_KEY and the model from APP_ANTHROPIC_MODEL. Default the model to claude-haiku-4-5-20251001.5. Instantiate Anthropic with the key passed explicitly, timeout 20 seconds, and max_retries 0. Do not read or set the global ANTHROPIC_API_KEY.6. Ask the model to use only supplied facts and policy and return only JSON with exactly: draft_reply as text, evidence_refs as a list of policy IDs, missing_information as a list of field names, and review_status as READY_FOR_HUMAN_REVIEW, NEEDS_INFORMATION, or BLOCKED.7. Validate those fields and types before displaying them. Correct structure does not prove correct content.8. The app must never send a message, approve a refund, or change a record.9. Support --simulate-timeout. It must make no API call, clear draft_reply, use review_status UNAVAILABLE, and show a manual fallback message.10. Support --offline-demo. It must make no API call, load a labelled prerecorded synthetic result from demo_outputs.json, and print an explicit line saying that no model API was called.11. If the provider or model response fails, show the same safe unavailable state rather than a traceback or stale draft.setup_env.py must ask for the app API key using hidden input, ask for the model with the default above, and write a project-only .env file. It must never print the key. .gitignore must exclude .env, .venv, Python caches, and pytest caches. .env.example must contain placeholders only.requirements.txt must pin these tested versions:anthropic==1.5.0python-dotenv==1.2.3pytest==9.1.1Tests must not call an external API. Use a fake model function to test a successful C1 result, invalid model output, timeout behaviour, all input files, offline outputs, and that setup_env.py writes the key without printing it.Before writing files, show the plan and stop for approval.

## 3. Course prompt: strengthen missing-delivery-date behaviour

> Strengthen only the missing-delivery-date behaviour.Before any model call, check whether the selected case has a delivery_date. If it is missing or empty, do not call the model. Return this deterministic result:- draft_reply: "Before Meridian Retail can assess whether this case falls within the two-day damage-reporting rule, please provide the delivery date. A human support agent will review the request once that information is available."- evidence_refs: ["P2", "P4"]- missing_information: ["delivery_date"]- review_status: "NEEDS_INFORMATION"Add a test that passes a fake model function which raises an error if called, then prove C2 returns the deterministic result without calling that function. Do not change C1, C3, the timeout path, the offline-demo path, the credential names, or any project boundary. Run python -m pytest -q and show the result.

**Result:** the app did not exist yet (prompt 2 was never approved), so Claude Code proposed building the full plan with this check included.

## Follow-up requests

4. "go ahead" - approved building the full plan plus the missing-delivery-date check.
5. "use orchestrator and fan out subagents" - the work was split across parallel subagents (app + demo + tests; setup script + tests) while config files and the README were written directly. Result: 36 tests passed.
6. "give me a TLDR" - plain-language summary of what was built.
7. "let's use UV for Python and test it out" - rebuilt `.venv` with uv, reran tests and the offline, timeout, and no-key modes; README setup switched to uv.
8. "I don't have an API key ... I do have the subscription" - explained that a Claude subscription does not include API access; options were offline demo mode, a Console API key, or calling Claude Code.
9. "yes do that" - added `experiments/claude_code_backend.py`, which runs the same flow through `claude -p` on the subscription. Course files unchanged.
10. "put all of this in a new git repo ... keep the repo public" and "include the prompt history" - this repository and this file.
