# Contributing

Start with the README and architecture. Small, tested changes are welcome. Use a new branch and pull request; describe the user-visible behavior and checks you ran.

Install `python -m pip install '.[dev,mcp]'`, run `python -m pytest`, and build with `python -m build`. Tests use generated screens and temporary tokens. For browser changes, run the host with `--demo`, exercise connect/disconnect, pause/resume, failed authentication, display/crop controls, download, and narrow layouts. Check browser console errors and keyboard access. Do not use a real desktop screenshot in issues, docs or test fixtures.

Keep real tokens, IPs, machine names, private file paths, screenshots and logs out of commits. Scan the staged tree and built archive, not only the working files. Do not add analytics, external frontend assets, wildcard CORS, token-in-URL shortcuts or unauthenticated screen routes. Treat adding control, recording or remote command execution as a separate security/design review, not a small extension of the screenshot API.

The initial native Windows/macOS capture acceptance remains pending. Platform bug reports should include OS/Python versions and a sanitized description, not secrets or identifiable screen data.
