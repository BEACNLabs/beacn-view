"""Viewer client: credentials go only to one explicitly configured origin."""

import json
import ssl

import httpx

from .security import read_token, validate_url


class ViewerClient:
    def __init__(self, url, token_file, ca_file=None):
        self.url = validate_url(url)
        self.token = read_token(token_file)
        self.verify = ssl.create_default_context(cafile=ca_file)

    def get(self, path, params=None):
        with httpx.Client(
            verify=self.verify, trust_env=False, follow_redirects=False, timeout=15
        ) as client:
            with client.stream(
                "GET",
                self.url + path,
                params=params,
                headers={"Authorization": "Bearer " + self.token},
            ) as response:
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Host returned HTTP {response.status_code}; check authentication and host availability"
                    )
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 20 * 1024 * 1024:
                        raise RuntimeError("Host response exceeded the 20 MiB limit")
                return bytes(data), response.headers

    def status(self):
        return json.loads(self.get("/api/status")[0])

    def monitors(self):
        return json.loads(self.get("/api/monitors")[0])

    def capture(self, **params):
        image, headers = self.get("/api/frame", params)
        if not image.startswith(b"\xff\xd8\xff") or not image.endswith(b"\xff\xd9"):
            raise RuntimeError("Host did not return a complete JPEG")
        return image, json.loads(headers["x-beacn-frame"])
