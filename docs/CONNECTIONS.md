# Connections and troubleshooting

## SSH tunnel: another computer

1. Start `beacn-view serve` **locally in the target's graphical session**.
2. On your viewing computer, run `ssh -N -L 8741:127.0.0.1:8741 your-user@your-host`.
3. Visit `http://127.0.0.1:8741` on the viewing computer and paste the token.
4. Stop the tunnel and/or host when finished. Disconnect clears only that browser session.

If port 8741 is already used on the viewing computer, use `-L 8742:127.0.0.1:8741` and browse port 8742. SSH setup is outside this package. On Windows, launching the host remotely over SSH can put it in the wrong session; launch from the visible desktop instead.

## HTTPS: phone or direct network viewer

Use a real hostname resolving to the host, a certificate with that hostname in its subject alternative names, and a viewer that trusts its issuing CA:

```sh
beacn-view serve --bind 0.0.0.0 --allow-host screen.example.com \
  --cert-file /private/certs/fullchain.pem --key-file /private/certs/key.pem
```

Only expose the chosen port to intended devices on your private network/VPN. The app does not change firewalls, DNS, VPNs or certificate stores. A certificate can come from your existing trusted private PKI or certificate provider. Do not bypass a browser certificate warning. To use an IP address, its certificate must contain the corresponding IP SAN and the host must allow that exact IP with `--allow-host`.

The browser loads the viewer from the host's own origin. Do not host the frontend elsewhere and add permissive CORS. Reverse proxies and remote IPv6 listener setups are not covered by the supplied recipes; use the documented path first.

## Common failures

| Symptom | Check |
|---|---|
| Invalid host header | Add the exact hostname or IPv4 address used in your URL with `--allow-host`; do not include the port. |
| Access token rejected | Correct file? Whitespace is trimmed. Token changes require restarting the host. |
| Desktop unavailable | Run in the unlocked graphical session. On Linux, check X11/DISPLAY permissions; on macOS, Screen Recording permission. |
| Black or wrong desktop | Locked/session-0/headless capture and protected video may not work. WSL does not capture the Windows desktop. |
| No updates | Check pause, manual refresh, hidden tab, host process, network and capture-age indicator. |
| Crop error | Both dimensions must be zero or both positive; the crop must fit inside the selected display. |
| Blurry text | Increase image width and JPEG quality, or crop the area of interest before scaling. |
| Browser token lost | Expected after reload/disconnect. It is intentionally not stored. |
| Full screen unavailable | Some mobile browsers do not support it. Use browser zoom/orientation instead. |

There is no UAC/login-screen bypass, Wayland portal integration, wake-on-LAN, audio capture or control injection. A source-size cap of 40 megapixels protects memory; crop unusually large displays.
