import os
import subprocess
import sys

import pytest

from beacn_view.client import ViewerClient
from beacn_view.security import create_token, read_token, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "http://screen.example",
        "ftp://localhost",
        "https://user:pass@screen.example",
        "https://screen.example/?token=x",
        "https://screen.example/path",
        "https://screen.example/#secret",
    ],
)
def test_unsafe_destinations_rejected(url):
    with pytest.raises(ValueError):
        validate_url(url)


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1:8741", "http://localhost:8741/", "https://screen.example:8741"],
)
def test_supported_destinations(url):
    assert validate_url(url) == url.rstrip("/")


def test_random_tokens_private_and_never_overwritten(tmp_path):
    p = create_token(tmp_path / "one.token")
    q = create_token(tmp_path / "two.token")
    assert read_token(p) != read_token(q) and len(read_token(p)) >= 43
    with pytest.raises(FileExistsError):
        create_token(p)
    if os.name != "nt":
        p.chmod(0o644)
        with pytest.raises(ValueError, match="owner-only"):
            read_token(p)


def test_host_refuses_non_tls_network_listener(tmp_path):
    p = create_token(tmp_path / "one.token")
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "beacn_view.cli",
            "serve",
            "--bind",
            "0.0.0.0",
            "--token-file",
            str(p),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0 and "require TLS" in r.stderr
    assert read_token(p) not in r.stderr + r.stdout


def test_client_does_not_follow_redirects_or_inherit_proxies(tmp_path, monkeypatch):
    p = create_token(tmp_path / "one.token")
    seen = {}

    class Response:
        status_code = 302

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class HTTP:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr("beacn_view.client.httpx.Client", HTTP)
    with pytest.raises(RuntimeError, match="302"):
        ViewerClient("https://screen.example", p).status()
    assert seen["trust_env"] is False and seen["follow_redirects"] is False
