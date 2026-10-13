import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from beacn_view.capture import CaptureService, CaptureUnavailable, DemoDesktop
from beacn_view.host import create_app

TOKEN = "t" * 43  # Non-secret fixture, never used by a deployed host.
AUTH = {"Authorization": "Bearer " + TOKEN}


@pytest.fixture
def client():
    return TestClient(create_app(TOKEN, DemoDesktop(), ["testserver"]))


@pytest.mark.parametrize("path", ["/api/status", "/api/monitors", "/api/frame"])
def test_every_screen_endpoint_requires_token(client, path):
    assert client.get(path).status_code == 401
    assert (
        client.get(path, headers={"Authorization": "Bearer wrong"}).status_code == 401
    )
    assert client.get(path + "?token=" + TOKEN).status_code == 401


def test_no_data_or_credentials_in_public_assets(client):
    page = client.get("/")
    assert page.status_code == 200 and TOKEN not in page.text
    assert "no-store" in page.headers["cache-control"]
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert client.get("/static/../security.py").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_origin_and_host_boundaries(client):
    assert (
        client.get(
            "/api/status", headers={**AUTH, "Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/status", headers={**AUTH, "Host": "untrusted.example"}
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/api/status", headers={**AUTH, "Origin": "http://testserver"}
        ).status_code
        == 200
    )


def test_read_only_api_and_status(client):
    status = client.get("/api/status", headers=AUTH).json()
    assert status["read_only"] and status["demo"] and not status["recording"]
    assert set(status) == {"name", "version", "read_only", "demo", "recording"}
    assert client.post("/api/frame", headers=AUTH).status_code == 405
    for path in ["/api/input", "/api/shell", "/api/shutdown"]:
        assert client.post(path, headers=AUTH).status_code == 404


def test_frame_dimensions_metadata_and_crop(client):
    r = client.get(
        "/api/frame?x=100&y=100&width=800&height=600&max_width=400", headers=AUTH
    )
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    image = Image.open(BytesIO(r.content))
    assert image.size == (400, 300)
    meta = json.loads(r.headers["x-beacn-frame"])
    assert meta["source"] == dict(left=100, top=100, width=800, height=600)
    assert meta["demo"] and meta["frame_id"] and meta["captured_at"]
    assert r.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "query",
    [
        "monitor=0",
        "monitor=2",
        "x=-1",
        "width=2",
        "x=1599&width=2&height=2",
        "max_width=319",
        "quality=96",
        "x=2000",
    ],
)
def test_invalid_capture_rejected(client, query):
    assert client.get("/api/frame?" + query, headers=AUTH).status_code == 400


def test_capture_failure_returns_clean_error():
    class Missing(DemoDesktop):
        def monitors(self):
            raise CaptureUnavailable("Desktop unavailable")

    c = TestClient(create_app(TOKEN, Missing(), ["testserver"]))
    r = c.get("/api/monitors", headers=AUTH)
    assert r.status_code == 503 and r.json() == {"detail": "Desktop unavailable"}


def test_negative_monitor_offsets_and_pixel_cap():
    class Offset(DemoDesktop):
        def monitors(self):
            return [dict(id=1, left=-1600, top=-100, width=1600, height=900)]

        def grab(self, region):
            return Image.new("RGB", (region["width"], region["height"]))

    raw, meta = CaptureService(Offset()).capture(x=100, y=100, width=500, height=300)
    assert meta["source"]["left"] == -1500 and meta["source"]["top"] == 0

    class Huge(Offset):
        def monitors(self):
            return [dict(id=1, left=0, top=0, width=10000, height=10000)]

        def grab(self, region):
            raise AssertionError("Oversized capture must never reach backend")

    with pytest.raises(ValueError, match="megapixels"):
        CaptureService(Huge()).capture()
