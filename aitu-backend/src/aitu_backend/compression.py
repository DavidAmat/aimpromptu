"""gzip for the JSON answers, and for nothing else.

The piano sheet answer is 0.5 to 1.5 MB of JSON, mostly the sustain cells of the two hand matrices,
and gzip makes it about 12 times smaller. From the Mac through the SSH tunnel that is the difference
between sending a megabyte and sending 100 KB on every change of the sheet (implementation 08,
plan section 9.7).

Starlette's ``GZipMiddleware`` compresses every answer except the SSE stream. Here it compresses
only JSON: the audio files are already compressed (mp3) or large (wav), and compressing them costs
time for nothing and turns the partial answers the player asks for when it seeks into something
else. The level is 5, not Starlette's 9: on the largest piece of the library, level 9 takes 35 ms
for 95 KB and level 5 takes 5 ms for 103 KB (measured in Phase 2).
"""

from __future__ import annotations

from starlette.datastructures import Headers
from starlette.middleware.gzip import GZipMiddleware, GZipResponder, IdentityResponder
from starlette.types import ASGIApp, Message, Receive, Scope, Send

#: Answers smaller than this are sent as they are: compressing them saves nothing.
MINIMUM_SIZE = 1024
COMPRESS_LEVEL = 5
COMPRESSED_TYPES = ("application/json",)


class _JsonOnlyResponder(GZipResponder):
    async def send_with_compression(self, message: Message) -> None:
        if message["type"] == "http.response.start":
            await super().send_with_compression(message)
            content_type = Headers(raw=message["headers"]).get("content-type", "")
            # The flag Starlette itself uses for the SSE stream: pass the body through untouched.
            if not content_type.startswith(COMPRESSED_TYPES):
                self.content_type_is_excluded = True
            return
        await super().send_with_compression(message)


class JsonGZipMiddleware(GZipMiddleware):
    """``GZipMiddleware`` that compresses JSON answers only."""

    def __init__(
        self, app: ASGIApp, minimum_size: int = MINIMUM_SIZE, compresslevel: int = COMPRESS_LEVEL
    ) -> None:
        super().__init__(app, minimum_size=minimum_size, compresslevel=compresslevel)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # pragma: no cover - websockets and lifespan
            await self.app(scope, receive, send)
            return
        accepts = "gzip" in Headers(scope=scope).get("Accept-Encoding", "")
        responder = (
            _JsonOnlyResponder(self.app, self.minimum_size, compresslevel=self.compresslevel)
            if accepts
            else IdentityResponder(self.app, self.minimum_size)
        )
        await responder(scope, receive, send)
