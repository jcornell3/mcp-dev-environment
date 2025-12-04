#!/usr/bin/env python3
"""
YouTube to MP3 MCP Server
Downloads YouTube videos and converts to MP3 with metadata preservation
"""

import asyncio
import sys
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp_logic import youtube_to_mp3

# Set up logging to stderr for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='[youtube-to-mp3] %(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

app = Server("youtube-to-mp3")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="youtube_to_mp3",
            description="Download YouTube video and convert to MP3 with metadata preservation (ID3 tags, album art). ⚠️ Legal Notice: Use only with permission - respect copyright and YouTube ToS. Recommended for: your own videos, public domain content, Creative Commons licensed content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_url": {
                        "type": "string",
                        "description": "YouTube video URL (e.g., https://www.youtube.com/watch?v=VIDEO_ID) or video ID"
                    },
                    "bitrate": {
                        "type": "string",
                        "enum": ["128k", "192k", "256k", "320k"],
                        "description": "Audio bitrate. 128k=low quality/small file, 192k=standard (default), 256k=high quality, 320k=maximum quality/large file",
                        "default": "192k"
                    },
                    "preserve_metadata": {
                        "type": "boolean",
                        "description": "Embed ID3 tags (title, artist, album, year, description) and album art (thumbnail) into MP3 file",
                        "default": True
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "Custom output filename (optional, defaults to video title). Do not include .mp3 extension",
                        "default": ""
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
        logging.info(f"call_tool called with name={name}, arguments={arguments}")

        if name == "youtube_to_mp3":
            video_url = arguments.get("video_url")
            bitrate = arguments.get("bitrate", "192k")
            preserve_metadata = arguments.get("preserve_metadata", True)
            output_filename = arguments.get("output_filename", "")

            logging.info(f"Processing video_url={video_url}, bitrate={bitrate}, preserve_metadata={preserve_metadata}")

            if not video_url:
                raise ValueError("video_url is required")

            # Validate bitrate
            valid_bitrates = ["128k", "192k", "256k", "320k"]
            if bitrate not in valid_bitrates:
                raise ValueError(f"Invalid bitrate. Must be one of: {', '.join(valid_bitrates)}")

            # Convert video
            import os
            downloads_dir = os.environ.get("DOWNLOADS_DIR", "/app/downloads")
            logging.info(f"Using downloads_dir={downloads_dir}")

            result = youtube_to_mp3(
                video_url=video_url,
                bitrate=bitrate,
                output_dir=downloads_dir,
                preserve_metadata=preserve_metadata,
                output_filename=output_filename
            )

            logging.info(f"Download succeeded: {result['data']['file_path']}")
            return [TextContent(type="text", text=result["content"][0]["text"])]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logging.error(f"Error in youtube_to_mp3: {str(e)}", exc_info=True)
        error_msg = f"❌ Error: {str(e)}\n\nTroubleshooting:\n"
        error_msg += "- Verify the YouTube URL is correct\n"
        error_msg += "- Check if video is public (not private/deleted)\n"
        error_msg += "- Ensure video has not been region-locked\n"
        error_msg += "- Try a different video to test\n"
        raise ValueError(error_msg)

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
