"""EXPERIMENT ONLY - not part of the course spec.

Runs the same review flow as app.py, but sends the prompt to Claude Code
(`claude -p`) so it uses your Claude subscription instead of an API key.
app.py and the course files are unchanged.

    uv run --no-project python experiments/claude_code_backend.py --case C1
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app  # noqa: E402

CLAUDE_MODEL = "haiku"
TIMEOUT_SECONDS = 120  # CLI start-up is slower than a direct SDK call
SYSTEM_PROMPT = (
    "You are a text-only drafting function. You have no tools. "
    "Reply with only the JSON object the user asks for."
)


def call_claude_code(prompt):
    # Drop API keys so the CLI uses the subscription login, not an API key.
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "APP_ANTHROPIC_API_KEY")}
    with tempfile.TemporaryDirectory() as workdir:
        proc = subprocess.run(
            [
                "claude", "-p",
                "--model", CLAUDE_MODEL,
                "--tools", "",
                "--setting-sources", "",
                "--strict-mcp-config",
                "--no-session-persistence",
                "--output-format", "text",
                "--system-prompt", SYSTEM_PROMPT,
            ],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env=env,
            cwd=workdir,
            check=True,
        )
    return proc.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description="Experiment: app.py flow via Claude Code")
    parser.add_argument("--case", required=True, choices=["C1", "C2", "C3"])
    args = parser.parse_args(argv)
    print("EXPERIMENT: model called through Claude Code (claude -p) on your "
          "subscription, not the Anthropic SDK.")
    app.run(args.case, model_fn=call_claude_code)
    return 0


if __name__ == "__main__":
    sys.exit(main())
