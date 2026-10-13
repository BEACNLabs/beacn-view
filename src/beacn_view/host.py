"""Authenticated, read-only host. There are no input or shell endpoints."""

import hmac
import json
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .capture import CaptureService, CaptureUnavailable
from .security import TOKEN_PATTERN

STATIC = Path(__file__).with_name("static")


def create_app(token, backend=None, allowed_hosts=None):
    if not TOKEN_PATTERN.fullmatch(token):
        raise ValueError("A generated access token is required")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    service = CaptureService(backend)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts or ["localhost", "127.0.0.1", "[::1]"],
    )

    @app.middleware("http")
    async def boundaries(request, call_next):
        origin = request.headers.get("origin")
        expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if origin and origin != expected:
            response = JSONResponse(
                {"detail": "Cross-origin requests are not allowed"}, status_code=403
            )
        else:
            response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "X-Frame-Options": "DENY",
                "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            }
        )
        return response

    def authorized(request: Request):
        candidate = request.headers.get("authorization", "")
        if not hmac.compare_digest(candidate.encode(), ("Bearer " + token).encode()):
            raise HTTPException(
                401, "Access token required", headers={"WWW-Authenticate": "Bearer"}
            )

    @app.exception_handler(CaptureUnavailable)
    async def unavailable(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=503)

    @app.get("/")
    def viewer():
        return FileResponse(STATIC / "index.html")

    @app.get("/static/{name}")
    def asset(name: str):
        if name not in ("app.js", "style.css", "icon.svg"):
            raise HTTPException(404)
        return FileResponse(STATIC / name)

    @app.get("/api/status", dependencies=[Depends(authorized)])
    def status():
        return {
            "name": "BEACN View",
            "version": __version__,
            "read_only": True,
            "demo": service.backend.demo,
            "recording": False,
        }

    @app.get("/api/monitors", dependencies=[Depends(authorized)])
    def monitors():
        return {"monitors": service.monitors()}

    @app.get("/api/frame", dependencies=[Depends(authorized)])
    def frame(
        monitor: int = 1,
        x: int = 0,
        y: int = 0,
        width: int = 0,
        height: int = 0,
        max_width: int = 1920,
        quality: int = 80,
    ):
        try:
            image, meta = service.capture(
                monitor, x, y, width, height, max_width, quality
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return Response(
            image,
            media_type="image/jpeg",
            headers={"X-Beacn-Frame": json.dumps(meta, separators=(",", ":"))},
        )

    return app
