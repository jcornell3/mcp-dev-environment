#!/usr/bin/env python3
"""
YouTube to MP3 MCP Server
Downloads YouTube videos and converts to MP3 with metadata preservation
"""

import asyncio
import sys
import os
import logging
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from mcp_logic import youtube_to_mp3
from google_drive import upload_to_drive, get_or_create_folder, is_drive_configured
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import Response
from fastapi.routing import Mount
import uvicorn

# Set up logging to stderr for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='[youtube-to-mp3-mcp] %(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
log = logging.getLogger(__name__)

mcp_app = Server("youtube-to-mp3")

@mcp_app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="youtube_to_mp3",
            description="Download YouTube video and convert to MP3 with metadata preservation (ID3 tags, album art). Optionally upload to Google Drive. ⚠️ Legal Notice: Use only with permission - respect copyright and YouTube ToS. Recommended for: your own videos, public domain content, Creative Commons licensed content.",
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
                    },
                    "upload_to_drive": {
                        "type": "boolean",
                        "description": "Upload MP3 file to Google Drive after conversion. Requires Google Drive credentials to be configured.",
                        "default": False
                    },
                    "drive_folder": {
                        "type": "string",
                        "description": "Google Drive folder name to upload to (optional, creates if doesn't exist, defaults to root)",
                        "default": ""
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
        logging.info(f"call_tool called with name={name}, arguments={arguments}")

        if name == "youtube_to_mp3":
            video_url = arguments.get("video_url")
            bitrate = arguments.get("bitrate", "192k")
            preserve_metadata = arguments.get("preserve_metadata", True)
            output_filename = arguments.get("output_filename", "")
            upload_to_drive_flag = arguments.get("upload_to_drive", False)
            drive_folder = arguments.get("drive_folder", "")

            logging.info(f"Processing video_url={video_url}, bitrate={bitrate}, preserve_metadata={preserve_metadata}, upload_to_drive={upload_to_drive_flag}")

            if not video_url:
                raise ValueError("video_url is required")

            # Validate bitrate
            valid_bitrates = ["128k", "192k", "256k", "320k"]
            if bitrate not in valid_bitrates:
                raise ValueError(f"Invalid bitrate. Must be one of: {', '.join(valid_bitrates)}")

            # Check Google Drive configuration if upload requested
            if upload_to_drive_flag and not is_drive_configured():
                raise ValueError(
                    "Google Drive upload requested but credentials not configured.\n"
                    "Please set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_DRIVE_CREDENTIALS_JSON environment variable."
                )

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

            # Upload to Google Drive if requested
            drive_result = None
            if upload_to_drive_flag:
                try:
                    logging.info("Uploading to Google Drive...")

                    # Get or create folder if specified, otherwise use default
                    folder_id = None
                    folder_name = drive_folder if drive_folder else "MCP-YouTube-to-MP3"
                    folder_id = get_or_create_folder(folder_name)
                    logging.info(f"Using Drive folder: {folder_name} (ID: {folder_id})")

                    # Upload file
                    drive_result = upload_to_drive(
                        file_path=result['data']['file_path'],
                        folder_id=folder_id,
                        file_name=None  # Use original filename
                    )

                    logging.info(f"Google Drive upload succeeded: {drive_result['file_id']}")

                    # Append Drive info to response
                    drive_info = f"\n\n☁️ Google Drive Upload:\n"
                    drive_info += f"- File ID: {drive_result['file_id']}\n"
                    drive_info += f"- View Link: {drive_result['web_view_link']}\n"
                    drive_info += f"- Folder: {folder_name}\n"
                    drive_info += f"- Status: ✅ Upload successful"

                    result["content"][0]["text"] += drive_info
                    result["data"]["google_drive"] = drive_result

                except Exception as e:
                    logging.error(f"Google Drive upload failed: {str(e)}")
                    error_info = f"\n\n☁️ Google Drive Upload:\n- Status: ❌ Upload failed\n- Error: {str(e)}"
                    result["content"][0]["text"] += error_info
                    result["data"]["google_drive"] = {"success": False, "error": str(e)}

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
    ) as (read_stream, write_stream):
        # MCP server handles the streams through the transport
        await mcp_app.run(
            read_stream,
            write_stream,
            mcp_app.create_initialization_options()
        )


# Messages endpoint - mount the SSE transport handler directly
# The transport maintains session correlation for POST requests to /messages
async def messages_endpoint(scope, receive, send):
    """Messages endpoint that delegates to SSE transport"""
    await sse_transport.handle_post_message(scope, receive, send)

app.routes.append(Mount("/messages", app=messages_endpoint))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "youtube-to-mp3",
        "api_key_configured": MCP_API_KEY != "default-api-key",
        "google_drive_configured": is_drive_configured()
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
