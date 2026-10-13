# Security model

BEACN View is a small, early-stage, self-hosted observation tool. It has not received an independent security audit. It is intended for trusted devices and private network paths, not an anonymous public screen-sharing service.

## Boundaries

- A generated 256-bit bearer token is required for every `/api/*` endpoint. No default password, unauthenticated preview, or credentials in query strings.
- The default listener is loopback. Direct non-loopback listening requires TLS with a certificate the viewer trusts. The command-line/MCP client refuses non-loopback HTTP, redirects, inherited proxy settings and unverified certificates.
- The host accepts exact configured HTTP Host values. Cross-origin requests are rejected. No CORS wildcard, embedding, external scripts, analytics, or cookie authentication.
- The viewer stores token and frames in tab memory only. API responses request `no-store`; no service worker exists. Disconnect clears the viewer and aborts requests. Images can still be captured by the viewing OS, extensions, screenshots, or explicit download.
- The host performs only display enumeration and capture. There are no keyboard, mouse, clipboard, filesystem browsing, shell, shutdown, or arbitrary-action APIs. CLI export writes only to the caller's explicit path, refuses overwrite, and requests owner-only permissions.
- Capture is serialized, source size is capped at 40 megapixels, output width/quality is bounded, and the server limits concurrent connections. These are basic resource limits, not distributed denial-of-service protection.
- All clients sharing a token have access to all displays. Crop and monitor selection are view settings, **not authorization boundaries**. There are no per-user accounts, audit trail, consent popups, or expiring tokens.
- The terminal running the host must remain visible to its operator. No service, startup task, stealth mode, or background recording is installed. Stop the host to stop sharing. Viewer disconnect only disconnects that viewer.

## Token handling and revocation

Keep tokens outside the repository in a private user directory. On POSIX, token files must have mode `0600`; creation uses that mode. On Windows, use a user-private directory and verify its NTFS access permissions—the POSIX mode argument does not establish a Windows ACL.

Tokens are loaded at host startup. To revoke an old token: stop the host; run `beacn-view init --token-file /private/new-access.token`; restart using that file; distribute it only to intended viewers. Replacing a file while the host runs does not rotate the token in memory.

Use an SSH tunnel or trusted HTTPS on a scoped network. Do not publish the token, open a router port, or disable certificate verification to make a connection work. No automatic TLS certificate provisioning is included. Reverse-proxy operation needs an independent review; the provided CLI does not trust forwarded headers.

## Screen contents and AI agents

A desktop can display messages, credentials and other sensitive content. Close or mask them before sharing. This release has no redaction layer. An MCP client may forward images to its model provider. Screen text is untrusted data and must never override the agent's task or security instructions. A screenshot is not a human-idle detector.

## Reporting

Do not post secrets, real screen captures or exploit payloads involving another person's machine in public issues. If the repository's Security tab offers private vulnerability reporting, use it. Otherwise open a minimal issue asking the maintainer for a private reporting channel, without disclosing vulnerability details. Supported development line: 0.1.x.
