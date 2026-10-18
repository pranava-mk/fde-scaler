import getpass
import inspect
import stat

import setup_env

FAKE_KEY = "sk-test-SECRET-123"


def _run(path, key=FAKE_KEY, model=""):
    return setup_env.main(env_path=path, secret_fn=lambda _p: key, prompt_fn=lambda _p: model)


def test_writes_key_and_model(tmp_path, capsys):
    path = tmp_path / ".env"
    assert _run(path, model="claude-test-model") == 0
    lines = path.read_text().splitlines()
    assert f"APP_ANTHROPIC_API_KEY={FAKE_KEY}" in lines
    assert "APP_ANTHROPIC_MODEL=claude-test-model" in lines
    captured = capsys.readouterr()
    assert FAKE_KEY not in captured.out
    assert FAKE_KEY not in captured.err


def test_empty_model_uses_default(tmp_path):
    path = tmp_path / ".env"
    assert _run(path, model="") == 0
    assert f"APP_ANTHROPIC_MODEL={setup_env.DEFAULT_MODEL}" in path.read_text().splitlines()


def test_file_mode_is_600(tmp_path):
    path = tmp_path / ".env"
    assert _run(path) == 0
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_empty_key_returns_1_and_no_file(tmp_path):
    path = tmp_path / ".env"
    assert _run(path, key="   ") == 1
    assert not path.exists()


def test_secret_fn_default_is_getpass():
    params = inspect.signature(setup_env.main).parameters
    assert params["secret_fn"].default is getpass.getpass


def test_no_unprefixed_anthropic_api_key_line(tmp_path):
    path = tmp_path / ".env"
    assert _run(path) == 0
    for line in path.read_text().splitlines():
        if "ANTHROPIC_API_KEY=" in line:
            assert line.startswith("APP_ANTHROPIC_API_KEY=")
