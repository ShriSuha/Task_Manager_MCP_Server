#!/usr/bin/env python3
"""
Task Tracker MCP Server (Streamable HTTP)
Same as server.py but over HTTP using MCP Streamable HTTP transport (single /mcp endpoint).
"""

import contextlib
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
    print("Task Tracker MCP (Streamable HTTP) at http://127.0.0.1:8000")
    print('Cursor MCP config: "url": "http://localhost:8000/mcp"')
    async with manager.run():
        yield


fastapi_app = FastAPI(lifespan=lifespan)
fastapi_app.mount("/mcp", mcp_asgi)


if __name__ == "__main__":
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000)
