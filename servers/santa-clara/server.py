#!/usr/bin/env python3
"""
Santa Clara Property Tax MCP Server
Uses MCP Python SDK with native HTTP support via FastAPI
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import Response
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[santa-clara-mcp] %(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
log = logging.getLogger(__name__)

# Initialize MCP server
server = Server("santa-clara")


# Real property data for Santa Clara County APNs
PROPERTY_DATABASE = {
    "288-12-033": {
        "apn": "288-12-033",
        "address": "337 APRIL WY CAMPBELL CA 95008",
        "owner": {
            "name": "Property Owner Name",
            "type": "individual"
        },
        "property_type": "residential",
        "assessed_value": 950000,
        "tax_amount": 11875,
        "year_built": 1972,
        "lot_size_sqft": 9375,
        "building_sqft": 1760,
        "bedrooms": 3,
        "bathrooms": 2,
        "last_sale_date": "2019-03-22",
        "last_sale_price": 875000,
        "status": "active",
        "county": "Santa Clara",
        "land_use_code": "R1",
        "parcel_number": "288-12-033"
    }
}


def generate_property_data(apn: str) -> dict:
    """Get property data from database or generate mock data for unknown APNs"""
    # Check if APN exists in our database
    if apn in PROPERTY_DATABASE:
        data = PROPERTY_DATABASE[apn].copy()
        data["retrieved_at"] = datetime.now().isoformat()
        return data

    # For unknown APNs, return error indicating not found
    raise ValueError(f"APN {apn} not found in database. This is a demonstration server with limited property data.")


@server.list_tools()
async def list_tools():
    """List available MCP tools"""
    return [
        Tool(
            name="get_property_info",
            description="Get property information by APN (Assessor's Parcel Number)",
            inputSchema={
                "type": "object",
                "properties": {
                    "apn": {
                        "type": "string",
                        "description": "Assessor's Parcel Number (e.g., 123-456-789)"
                    }
                },
                "required": ["apn"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Execute MCP tool"""
    if name == "get_property_info":
        apn = arguments.get("apn")
        if not apn:
            raise ValueError("APN is required")

        # Generate property data
        data = generate_property_data(apn)

        # Format response
        text_response = f"""Property Information for APN: {apn}

Address: {data['address']}
Owner: {data['owner']['name']}
Property Type: {data['property_type']}
Assessed Value: ${data['assessed_value']:,}
Tax Amount: ${data['tax_amount']:,.0f}
Year Built: {data['year_built']}
Lot Size: {data['lot_size_sqft']:,} sqft
Building Size: {data['building_sqft']:,} sqft"""

        return [
            TextContent(
                type="text",
                text=text_response
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")


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
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


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
        "service": "santa-clara",
        "api_key_configured": MCP_API_KEY != "default-api-key"
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
