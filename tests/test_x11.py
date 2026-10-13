"""Optional real MSS capture against a disposable Xvfb desktop, never a user screen."""

import os
from io import BytesIO

import pytest
from PIL import Image

from beacn_view.capture import CaptureService


@pytest.mark.skipif(
    os.environ.get("BEACN_TEST_X11") != "1",
    reason="Run explicitly inside a disposable Xvfb display",
)
def test_native_x11_capture():
    raw, meta = CaptureService().capture()
    assert not meta["demo"]
    assert Image.open(BytesIO(raw)).size == (800, 600)
    assert meta["source"]["width"] == 800 and meta["source"]["height"] == 600
