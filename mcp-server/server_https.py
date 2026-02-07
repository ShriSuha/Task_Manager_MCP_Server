#!/usr/bin/env python3
"""
Task Tracker MCP Server (Streamable HTTP — production)
Same as server_http.py but bound for cloud deployment:
- Listens on 0.0.0.0 (all interfaces) so it's reachable from the internet.
- Uses PORT from environment (Railway, Render, Heroku set this).
Use this file when deploying to Railway, Render, or Heroku.
"""

import contextlib
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

# Reuse the same app and logic as the stdio server
from server import app, load_tasks

# Streamable HTTP: single endpoint. Stateless = no session ID required (Cursor doesn't send it back).
manager = StreamableHTTPSessionManager(app, json_response=True, stateless=True)

# Cursor and some clients don't send Accept: text/event-stream; the SDK rejects them.
# Inject it so the server accepts the request. We use json_response=True so we never actually stream SSE.
ACCEPT_BOTH = (b"accept", b"text/event-stream, application/json")


async def mcp_asgi(scope, receive, send):
    headers = list(scope.get("headers", []))
    # Remove any existing accept header so our injection is the only one
    headers = [(k, v) for k, v in headers if k.lower() != b"accept"]
    headers.append(ACCEPT_BOTH)
    scope = {**scope, "headers": headers}
    await manager.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(_app):
    load_tasks()
    port = int(os.environ.get("PORT", "8000"))
    print(f"Task Tracker MCP (Streamable HTTP) listening on 0.0.0.0:{port}")
    print('Cursor MCP config: "url": "https://taskmanagermcpserver-production.up.railway.app/mcp"')
    async with manager.run():
        yield

fastapi_app = FastAPI(lifespan=lifespan)

# Add CORS middleware to allow requests from Cursor
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you might want to restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@fastapi_app.get("/")
async def health_check():
    return {"status": "ok", "service": "task-tracker-mcp"}

fastapi_app.mount("/mcp", mcp_asgi)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port)
