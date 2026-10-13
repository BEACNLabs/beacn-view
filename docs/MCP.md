# Read-only MCP viewer

Run the host in the target's interactive graphical session. Run the MCP process on the agent computer. Install from a clone with `python -m pip install '.[mcp]'`. Provide the host token through a local protected file transferred over a trusted channel.

A standard stdio MCP connection definition:

```json
{
  "mcpServers": {
    "beacn-view": {
      "command": "/absolute/path/to/.venv/bin/beacn-view",
      "args": [
        "mcp", "--url", "http://127.0.0.1:8741",
        "--token-file", "/private/path/access.token"
      ]
    }
  }
}
```

Use your client's configuration format; the example describes the command and arguments. On Windows, the executable is `.venv\Scripts\beacn-view.exe`. For a remote host, use `https://screen.example.com:8741`, or establish an SSH tunnel and retain the loopback URL. For your own CA, add `--ca-file /path/to/trusted-ca.pem`. There is no insecure certificate flag.

Tools:

- `screen_status {}`: host version, read-only and demo flags. Reachability does not guarantee screen-capture permission.
- `screen_monitors {}`: display IDs and geometry.
- `screen_capture {"monitor":1,"max_width":1920,"quality":80}`: image content and frame metadata.
- Cropped capture: `screen_capture {"monitor":1,"x":100,"y":100,"width":800,"height":600}`. X/Y are relative to that monitor. Returned source coordinates are desktop-absolute; image coordinates may be scaled. Do not confuse the two.

There are no control tools. The existing terminal tools of an agent remain separate. Each call captures only when requested; connecting MCP alone does not start a monitoring loop. Do not add continuous observation to unrelated tasks.

Example agent request: “Take one screen capture of my test desktop and tell me whether the build window shows an error. Do not interact with it.”
