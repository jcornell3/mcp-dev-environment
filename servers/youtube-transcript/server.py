#!/usr/bin/env python3
"""
YouTube Transcript MCP Server
Retrieves transcripts from YouTube videos
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp_logic import get_transcript, list_available_languages

app = Server("youtube-transcript")

@app.list_tools()
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
                        "description": "Include timestamps in the output",
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

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a tool"""
    try:
        if name == "get_transcript":
            video_url = arguments.get("video_url")
            language = arguments.get("language", "en")
            include_timestamps = arguments.get("include_timestamps", False)

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

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
