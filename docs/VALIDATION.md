# Validation scope — v0.1.0

Release checks performed on 2026-10-13:

- 30 automated Python checks passed: every screen endpoint requires authentication; cross-origin and unexpected-host rejection; no control endpoints; crop/size bounds; private token permissions; HTTPS URL restrictions; redirect/proxy refusal; actual stdio MCP initialization, discovery, image response and rejected invalid/unknown tool calls.
- Native MSS capture passed against a disposable **800×600 X11/Xvfb desktop**, independent of the demo backend. This confirms the native Linux capture path without using a person's screen.
- Browser acceptance passed on **Chromium, Firefox and WebKit**, at **1440×1000** and **390×844** CSS pixels. Exercised rejected token, connect, pause/resume, manual capture, zoom, crop, JPEG download, disconnect, late-response discard, and empty browser storage/cookies.
- Automated axe scans: no violations in those six connected views. No JavaScript exceptions or page-width overflow. This is not a complete accessibility audit.
- Desktop/mobile synthetic screenshots were visually reviewed. README artwork is captured from the demo backend only.
- Source distribution and wheel built; package contents reviewed. Dependency audit performed against the isolated development environment. No known vulnerabilities reported after updating the development environment's pip.
- Publication scan covers staged source, documentation, image metadata, and built archives for private endpoints, machine names, local environment paths, excluded product names, credentials, or unexpected files. Fresh repository history; no private project history imported.

GitHub-hosted validation also passed all seven jobs in the [initial release CI run](https://github.com/BEACNLabs/beacn-view/actions/runs/38446229469): Python 3.11/3.13 on Windows, macOS and Linux, plus browser and isolated X11 checks. A fresh wheel installation independently served the bundled viewer and returned a synthetic frame.

Not yet accepted: native Windows/macOS capture, real Android/iOS hardware, Wayland, secure/login desktop, multi-monitor hardware, high-DPI native device behavior, long-session performance or independent security review. Monitor-offset/crop behavior is exercised with generated test geometry. No actual desktop input is implemented or tested.

Reproduce:

```sh
python -m pip install '.[dev,mcp]'
python -m pytest
# Linux only, deliberately isolated display; requires Xvfb and xauth:
xvfb-run -a -s '-screen 0 800x600x24' env BEACN_TEST_X11=1 python -m pytest tests/test_x11.py
npm ci
npx playwright install --with-deps
npm test  # set PYTHON to your virtual environment's Python when needed
python -m build
```

Default Python tests skip the explicit X11 check. Browser tests create an authenticated synthetic host, run on loopback, and terminate it afterwards. CI runs portable Python tests/builds on Windows, macOS and Linux; those jobs do not qualify capture against a real desktop on each OS.
