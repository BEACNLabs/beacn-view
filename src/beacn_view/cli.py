import argparse
import json
import os
from pathlib import Path

from .security import DEFAULT_TOKEN, create_token, read_token


def main():
    parser = argparse.ArgumentParser(
        description="BEACN View — self-hosted screen observation"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a fresh access token; never overwrites")
    init.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN)
    host = sub.add_parser("serve", help="Run the capture host in your desktop session")
    host.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN)
    host.add_argument("--bind", default="127.0.0.1")
    host.add_argument("--port", type=int, default=8741)
    host.add_argument("--allow-host", action="append", default=[])
    host.add_argument("--cert-file")
    host.add_argument("--key-file")
    host.add_argument(
        "--demo",
        action="store_true",
        help="Use generated sample content; never capture a desktop",
    )
    for name in ("capture", "mcp"):
        client = sub.add_parser(
            name,
            help="Save one frame"
            if name == "capture"
            else "Start the read-only stdio MCP viewer",
        )
        client.add_argument("--url", required=True)
        client.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN)
        client.add_argument(
            "--ca-file",
            help="Optional trusted CA file for your private HTTPS certificate",
        )
        if name == "capture":
            client.add_argument("--output", type=Path, required=True)
            client.add_argument("--monitor", type=int, default=1)
            client.add_argument("--max-width", type=int, default=1920)
    args = parser.parse_args()
    try:
        if args.command == "init":
            path = create_token(args.token_file)
            print(
                f"Access token created at {path}\nOpen that file locally and paste its contents into the viewer. Keep it private."
            )
        elif args.command == "serve":
            if bool(args.cert_file) != bool(args.key_file):
                parser.error("Supply both --cert-file and --key-file")
            if (
                args.bind not in ("127.0.0.1", "::1", "localhost")
                and not args.cert_file
            ):
                parser.error(
                    "Non-loopback listeners require TLS (--cert-file and --key-file). Alternatively use an SSH tunnel."
                )
            if not 1 <= args.port <= 65535:
                parser.error("Port must be between 1 and 65535")
            if any("*" in h or "/" in h or ":" in h for h in args.allow_host):
                parser.error(
                    "--allow-host must be an exact DNS hostname or IPv4 address, without port or wildcards"
                )
            import uvicorn

            from .capture import DemoDesktop
            from .host import create_app

            hosts = ["localhost", "127.0.0.1", "[::1]"] + args.allow_host
            if args.bind not in ("0.0.0.0", "::"):
                hosts.append(args.bind if args.bind != "::1" else "[::1]")
            app = create_app(
                read_token(args.token_file), DemoDesktop() if args.demo else None, hosts
            )
            print(
                "BEACN View: read-only host. Stop with Ctrl+C. No recording or background installation.",
                flush=True,
            )
            if args.demo:
                print("DEMO MODE: generated content only.", flush=True)
            uvicorn.run(
                app,
                host=args.bind,
                port=args.port,
                ssl_certfile=args.cert_file,
                ssl_keyfile=args.key_file,
                access_log=False,
                proxy_headers=False,
                limit_concurrency=16,
            )
        else:
            from .client import ViewerClient

            client = ViewerClient(args.url, args.token_file, args.ca_file)
            if args.command == "capture":
                # Reserve the path before observing; never replace an existing file.
                fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    with os.fdopen(fd, "wb") as f:
                        image, meta = client.capture(
                            monitor=args.monitor, max_width=args.max_width
                        )
                        f.write(image)
                except Exception:
                    args.output.unlink(missing_ok=True)
                    raise
                print(json.dumps(meta))
            else:
                from .mcp_server import run

                run(client)
    except (OSError, ValueError, RuntimeError) as exc:
        # Transport tracebacks can include environment paths; keep operational output brief.
        parser.exit(1, f"{type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
