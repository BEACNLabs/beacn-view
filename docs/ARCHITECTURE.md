# Architecture and HTTP API

`capture.py` enumerates local displays and reads pixels using MSS, converts with Pillow and returns a JPEG. `host.py` serves a small same-origin browser app and authenticated API through FastAPI/Uvicorn. `client.py` is the HTTP viewer used by the CLI and optional `mcp_server.py`. `DemoDesktop` is an injectable synthetic backend, used by examples/tests only when explicitly selected.

No external remote-desktop protocol or existing proprietary host is needed. Source is independently implemented for this project. The repository has a fresh history and contains only public code and generated examples.

## API v1 (initial, not yet a stable versioned contract)

Every endpoint below requires `Authorization: Bearer <private-token>`:

| Method / path | Response |
|---|---|
| `GET /api/status` | `{name, version, read_only, demo, recording}` |
| `GET /api/monitors` | `{monitors: [{id, left, top, width, height}, ...]}` |
| `GET /api/frame` | JPEG, plus JSON metadata in `X-Beacn-Frame` |

Frame query parameters: `monitor=1`, `x=0`, `y=0`, `width=0`, `height=0`, `max_width=1920`, `quality=80`. Both crop dimensions zero means the remainder of the display starting at X/Y. Monitor IDs start at 1. No “all displays” capture mode is exposed. `max_width` is 320–7680; quality 30–95. Captures are never upscaled.

Metadata: `frame_id`, `captured_at` (UTC acquisition start), `monitor`, `source` (`left`, `top`, `width`, `height` in desktop pixels), output `width`/`height`, `demo`. No hostname, username, filenames or system inventory is returned. The source region can have negative offsets on multi-monitor desktops.

Status errors: 401 authentication; 400 invalid crop/parameters; 422 malformed typed query; 503 unavailable desktop. Browser assets are public, but contain no screen data or token. API responses request no storage. There are no cookies or cross-origin access grants.

## State and limits

The browser issues one request at a time and aborts in-flight requests on disconnect/settings changes. Epoch checks discard late responses. Hidden tabs stop polling; manual refresh and pause retain the current image, with its age visible. Disconnect revokes blob URLs and clears image/token state. Network failures leave a visibly stale image rather than falsely claiming an updated frame.

Host capture is serialized within one process. Use the supplied single-worker CLI; multiple ASGI workers are not an advertised mode. There is no persistent frame store or token database. A host token authorizes every display, not just a selected crop.
