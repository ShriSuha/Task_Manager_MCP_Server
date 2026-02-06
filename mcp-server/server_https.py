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

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

# Reuse the same app and logic as the stdio server
from server import app, load_tasks

# Streamable HTTP: single endpoint handles both POST (send) and GET (optional SSE stream)
manager = StreamableHTTPSessionManager(app, json_response=True)


async def mcp_asgi(scope, receive, send):
    await manager.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(_app):
    load_tasks()
    port = int(os.environ.get("PORT", "8000"))
    print(f"Task Tracker MCP (Streamable HTTP) listening on 0.0.0.0:{port}")
    print('Cursor MCP config: "url": "https://<your-app-url>/mcp"')
    async with manager.run():
        yield


fastapi_app = FastAPI(lifespan=lifespan)
fastapi_app.mount("/mcp", mcp_asgi)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port)
