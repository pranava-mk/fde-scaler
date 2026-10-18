import getpass
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

_QUOTES = ("'", '"', "`")


def main(env_path=ENV_PATH, secret_fn=getpass.getpass, prompt_fn=input) -> int:
    env_path = Path(env_path)
    key = secret_fn("APP_ANTHROPIC_API_KEY (input hidden): ").strip()
    if not key:
        print("No key entered. .env not written.", file=sys.stderr)
        return 1
    if any(c.isspace() or c in _QUOTES for c in key):
        print("Invalid key format. .env not written.", file=sys.stderr)
        return 1
    model = prompt_fn(f"APP_ANTHROPIC_MODEL [{DEFAULT_MODEL}]: ").strip() or DEFAULT_MODEL
    content = f"APP_ANTHROPIC_API_KEY={key}\nAPP_ANTHROPIC_MODEL={model}\n"
    fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(content)
    os.chmod(env_path, 0o600)
    print(f"Wrote {env_path.name} (project-only, permissions 600). The key was not displayed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
