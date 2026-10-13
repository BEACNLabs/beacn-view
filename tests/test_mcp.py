"""Real stdio transport against a synthetic host; no real screen is read."""

import base64
import json
import socket
import subprocess
import sys
import time

import anyio
import httpx
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from beacn_view.security import create_token


def test_mcp_end_to_end(tmp_path):
    token = create_token(tmp_path / "test.token")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    host = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "beacn_view.cli",
            "serve",
            "--demo",
            "--port",
            str(port),
            "--token-file",
            str(token),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for attempt in range(100):
            try:
                if httpx.get(url, timeout=0.2, trust_env=False).status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(0.1)
        else:
            raise AssertionError("Demo host did not start")

        async def check():
            params = StdioServerParameters(
                command=sys.executable,
                args=[
                    "-m",
                    "beacn_view.cli",
                    "mcp",
                    "--url",
                    url,
                    "--token-file",
                    str(token),
                ],
            )
            async with stdio_client(params) as (r, w), ClientSession(r, w) as client:
                await client.initialize()
                tools = await client.list_tools()
                assert {t.name for t in tools.tools} == {
                    "screen_status",
                    "screen_monitors",
                    "screen_capture",
                }
                result = await client.call_tool("screen_capture", {"max_width": 800})
                assert not result.is_error
                metadata = json.loads(result.content[0].text)
                assert metadata["demo"] and metadata["width"] == 800
                assert base64.b64decode(result.content[1].data).startswith(
                    b"\xff\xd8\xff"
                )
                invalid = await client.call_tool("screen_capture", {"quality": 99})
                assert invalid.is_error
                unavailable = await client.call_tool(
                    "type_text", {"text": "never sent"}
                )
                assert unavailable.is_error

        anyio.run(check)
    finally:
        host.terminate()
        host.wait(timeout=10)
