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
from fastapi.routing import Mount
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
    "288-13-033": {
        "apn": "288-13-033",
        "apn_suffix": "00",
        "address": "1373 CRONWELL DR CAMPBELL CA 95008",
        "owner": {
            "name": "Property Owner Name",
            "type": "individual"
        },
        "property_type": "residential",
        "tax_rate_area": "010-025",
        "tax_year": "2025/2026",
        "annual_tax_bill": 3695.40,
        "installment_1": {
            "tax_amount": 1847.70,
            "additional_charges": 0.00,
            "amount_paid": 1847.70,
            "balance_due": 0.00,
            "pay_by_date": "12/10/2025",
            "status": "PAID",
            "last_payment_date": "10/09/2025"
        },
        "installment_2": {
            "tax_amount": 1847.70,
            "additional_charges": 0.00,
            "amount_paid": 0.00,
            "balance_due": 1847.70,
            "pay_by_date": "04/10/2026",
            "status": "DUE",
            "last_payment_date": "N/A"
        },
        "county": "Santa Clara",
        "parcel_number": "288-13-033"
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
Tax Rate Area: {data['tax_rate_area']}
Property Type: {data['property_type']}

2025/2026 Annual Tax Bill: ${data['annual_tax_bill']:,.2f}

Installment 1:
  Amount: ${data['installment_1']['tax_amount']:,.2f}
  Status: {data['installment_1']['status']}
  Paid: ${data['installment_1']['amount_paid']:,.2f}
  Balance Due: ${data['installment_1']['balance_due']:,.2f}
  Pay By: {data['installment_1']['pay_by_date']}
  Last Payment: {data['installment_1']['last_payment_date']}

Installment 2:
  Amount: ${data['installment_2']['tax_amount']:,.2f}
  Status: {data['installment_2']['status']}
  Paid: ${data['installment_2']['amount_paid']:,.2f}
  Balance Due: ${data['installment_2']['balance_due']:,.2f}
  Pay By: {data['installment_2']['pay_by_date']}
  Last Payment: {data['installment_2']['last_payment_date']}"""

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
        "service": "santa-clara",
        "api_key_configured": MCP_API_KEY != "default-api-key"
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
