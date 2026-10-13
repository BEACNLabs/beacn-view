import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlsplit

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43,128}\Z")
DEFAULT_TOKEN = Path.home() / ".beacn-view" / "access.token"


def create_token(path):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(secrets.token_urlsafe(32) + "\n")
    return path


def read_token(path):
    path = Path(path).expanduser()
    if os.name != "nt" and path.stat().st_mode & 0o077:
        raise ValueError("Token file must have owner-only permissions (chmod 600)")
    value = path.read_text().strip()
    if not TOKEN_PATTERN.fullmatch(value):
        raise ValueError("Invalid token file. Generate one using beacn-view init.")
    return value


def validate_url(url):
    parts = urlsplit(url)
    if (
        parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or parts.path not in ("", "/")
        or not parts.hostname
    ):
        raise ValueError(
            "Host URL must contain only a scheme, hostname and optional port"
        )
    if parts.scheme != "https" and not (
        parts.scheme == "http" and parts.hostname in ("localhost", "127.0.0.1", "::1")
    ):
        raise ValueError(
            "Use HTTPS for remote hosts, or HTTP through a loopback SSH tunnel"
        )
    return url.rstrip("/")
