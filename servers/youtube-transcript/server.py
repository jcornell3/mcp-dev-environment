#!/usr/bin/env python3
"""
YouTube Transcript MCP Server
Retrieves transcripts from YouTube videos
"""

import asyncio
import sys
import os
import logging
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from mcp_logic import get_transcript, list_available_languages
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import Response
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[youtube-transcript-mcp] %(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
log = logging.getLogger(__name__)

mcp_app = Server("youtube-transcript")

@mcp_app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_transcript",
            description="Get the transcript/captions of a YouTube video",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_url": {
                        "type": "string",
                        "description": "YouTube video URL (e.g., https://www.youtube.com/watch?v=VIDEO_ID) or video ID"
                    },
                    "language": {
                        "type": "string",
                        "description": "Language code (e.g., 'en', 'es', 'fr'). Defaults to 'en'",
                        "default": "en"
                    },
                    "include_timestamps": {
                        "type": "boolean",
                        "description": "Include timestamps in the output (default: false)",
                        "default": False
                    }
                },
                "required": ["video_url"]
            }
        ),
        Tool(
            name="list_available_languages",
            description="List available transcript languages for a YouTube video",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_url": {
                        "type": "string",
                        "description": "YouTube video URL or video ID"
                    }
                },
                "required": ["video_url"]
            }
        )
    ]

@mcp_app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a tool"""
    try:
        if name == "get_transcript":
            video_url = arguments.get("video_url")
            language = arguments.get("language", "en")
            # Always disable timestamps - ignore user input
            include_timestamps = False

            result = get_transcript(video_url, language, include_timestamps)
            return [TextContent(type="text", text=result["content"][0]["text"])]

        elif name == "list_available_languages":
            video_url = arguments.get("video_url")
            result = list_available_languages(video_url)
            return [TextContent(type="text", text=result["content"][0]["text"])]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        raise ValueError(f"Error: {str(e)}")

# FastAPI app
app = FastAPI(title="Math MCP Server")

# Get API key from environment
MCP_API_KEY = os.environ.get("MCP_API_KEY", "default-api-key")

# Global SSE transport instance - shared across /sse and /messages endpoints
# This maintains session state and correlates SSE streams with POST messages
sse_transport = SseServerTransport(endpoint="/messages")


# Authentication middleware for SSE endpoints
async def verify_auth_header(request: Request) -> str:
    """Verify authorization header and return token"""
    auth_header = request.headers.get("authorization", "")

    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    token = parts[1]
    if token != MCP_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return token


# Create a new SSE transport for each connection
def create_sse_transport():
    """Create a new SSE transport instance"""
    return SseServerTransport(endpoint="/messages")


# SSE endpoint - handles WebSocket-like SSE stream (also accept /sse/)
@app.get("/sse")
@app.get("/sse/")
async def sse_stream(request: Request):
    """Server-Sent Events endpoint for MCP protocol"""
    await verify_auth_header(request)

    # Use global transport instance to maintain session state
    async with sse_transport.connect_sse(
        request.scope,
        request.receive,
        request._send
    ) as sse:
        await sse


# Messages endpoint - handles POST messages from client (also accept /messages/)
@app.post("/messages")
@app.post("/messages/")
async def messages_handler(request: Request):
    """Messages endpoint for MCP protocol"""
    await verify_auth_header(request)

    # Use global transport instance to correlate with SSE stream
    return await sse_transport.handle_post_message(
        request.scope,
        request.receive,
        request._send
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "youtube-transcript",
        "api_key_configured": MCP_API_KEY != "default-api-key"
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
