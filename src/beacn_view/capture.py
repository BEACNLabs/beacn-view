"""Capture only the local desktop; no external service or protocol is involved."""

import threading
import uuid
from datetime import UTC, datetime
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

MAX_PIXELS = 40_000_000


class CaptureUnavailable(Exception):
    pass


class Desktop:
    demo = False

    def monitors(self):
        import mss

        try:
            with mss.MSS() as screen:
                return [
                    {
                        "id": i,
                        **{k: int(m[k]) for k in ("left", "top", "width", "height")},
                    }
                    for i, m in enumerate(screen.monitors)
                    if i > 0
                ]
        except Exception as exc:
            raise CaptureUnavailable(
                "Desktop unavailable. Run the host in an unlocked graphical session with screen-capture permission."
            ) from exc

    def grab(self, region):
        import mss

        try:
            with mss.MSS() as screen:
                shot = screen.grab(region)
                return Image.frombytes("RGB", shot.size, shot.rgb)
        except Exception as exc:
            raise CaptureUnavailable(
                "Screen capture failed. Check the host session and OS capture permission."
            ) from exc


class DemoDesktop:
    """A generated, clearly labeled scene. Never reads a real screen."""

    demo = True

    def monitors(self):
        return [dict(id=1, left=0, top=0, width=1600, height=900)]

    def grab(self, region):
        image = Image.new("RGB", (1600, 900), "#111b2a")
        d = ImageDraw.Draw(image)
        def font(size):
            return ImageFont.load_default(size=size)
        d.rectangle((0, 0, 1600, 62), fill="#1b2a3d")
        d.text(
            (30, 20),
            "SYNTHETIC DEMO  /  no real desktop data",
            fill="#81e6c1",
            font=font(20),
        )
        d.rounded_rectangle(
            (65, 110, 1535, 805), radius=20, fill="#0b1220", outline="#304054", width=2
        )
        d.text((110, 156), "Build station", fill="#f3f7fc", font=font(36))
        d.text(
            (110, 216),
            "A quiet window into work in progress.",
            fill="#9eafc6",
            font=font(22),
        )
        lines = [
            ("> run verification", "#bbcde2"),
            ("  Package checks ................ passed", "#80e6c1"),
            ("  Browser checks ................ passed", "#80e6c1"),
            ("  Screen viewer ................. connected", "#80e6c1"),
            ("", "#bbcde2"),
            ("  Waiting for the next task.", "#bbcde2"),
        ]
        for i, (text, color) in enumerate(lines):
            d.text((115, 315 + i * 54), text, fill=color, font=font(25))
        d.text(
            (110, 741),
            "Sample content only  |  BEACN View",
            fill="#8eabc5",
            font=font(18),
        )
        return image.crop(
            (
                region["left"],
                region["top"],
                region["left"] + region["width"],
                region["top"] + region["height"],
            )
        )


class CaptureService:
    def __init__(self, backend=None):
        self.backend = backend or Desktop()
        self.lock = threading.Lock()

    def monitors(self):
        with self.lock:
            return self.backend.monitors()

    def capture(
        self, monitor=1, x=0, y=0, width=0, height=0, max_width=1920, quality=80
    ):
        values = (monitor, x, y, width, height, max_width, quality)
        if any(type(v) is not int for v in values):
            raise ValueError("Capture parameters must be integers")
        if (
            monitor < 1
            or min(x, y, width, height) < 0
            or not 320 <= max_width <= 7680
            or not 30 <= quality <= 95
        ):
            raise ValueError("Capture parameters out of range")
        if (width == 0) != (height == 0):
            raise ValueError("Specify both crop dimensions, or neither")
        with self.lock:
            monitors = self.backend.monitors()
            m = next((m for m in monitors if m["id"] == monitor), None)
            if m is None:
                raise ValueError("Monitor not found")
            if width == height == 0:
                width, height = m["width"] - x, m["height"] - y
            if (
                width <= 0
                or height <= 0
                or x + width > m["width"]
                or y + height > m["height"]
            ):
                raise ValueError("Crop falls outside the selected monitor")
            if width * height > MAX_PIXELS:
                raise ValueError(
                    "Capture exceeds 40 megapixels; request a smaller crop"
                )
            region = dict(
                left=m["left"] + x, top=m["top"] + y, width=width, height=height
            )
            captured_at = datetime.now(UTC).isoformat()
            image = self.backend.grab(region)
        if image.width > max_width:
            image = image.resize(
                (max_width, max(1, round(image.height * max_width / image.width))),
                Image.Resampling.LANCZOS,
            )
        output = BytesIO()
        image.save(output, format="JPEG", quality=quality)
        return output.getvalue(), dict(
            frame_id=str(uuid.uuid4()),
            captured_at=captured_at,
            monitor=monitor,
            source=region,
            width=image.width,
            height=image.height,
            demo=self.backend.demo,
        )
