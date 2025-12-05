#!/usr/bin/env python3
"""
Math Operations MCP Server
Uses MCP Python SDK with native HTTP/SSE support via FastAPI
Provides mathematical calculation and factorial tools
"""

import asyncio
import sys
import math
import json
import os
import logging
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import Response
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[math-mcp] %(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
log = logging.getLogger(__name__)

# Initialize MCP server
server = Server("math")


def calculate(operation: str, a: float, b: float = None) -> float:
    """Perform mathematical calculations"""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    elif operation == "power":
        return a ** b
    elif operation == "sqrt":
        if a < 0:
            raise ValueError("Cannot take square root of negative number")
        return math.sqrt(a)
    else:
        raise ValueError(f"Unknown operation: {operation}")


def factorial(n: int) -> int:
    """Calculate factorial of n"""
    if not isinstance(n, int) or n < 0:
        raise ValueError("Factorial requires a non-negative integer")
    if n > 100:
        raise ValueError("Factorial input must be <= 100")

    if n == 0 or n == 1:
        return 1

    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


@server.list_tools()
async def list_tools():
    """List available MCP tools"""
    return [
        Tool(
            name="calculate",
            description="Perform mathematical calculations (add, subtract, multiply, divide, power, sqrt)",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide", "power", "sqrt"],
                        "description": "The mathematical operation to perform"
                    },
                    "a": {
                        "type": "number",
                        "description": "First number (required for all operations)"
                    },
                    "b": {
                        "type": "number",
                        "description": "Second number (required for all operations except sqrt)"
                    }
                },
                "required": ["operation", "a"]
            }
        ),
        Tool(
            name="factorial",
            description="Calculate factorial of a number (0-100)",
            inputSchema={
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "The number to calculate factorial for (0-100)"
                    }
                },
                "required": ["n"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Execute MCP tool"""
    if name == "calculate":
        operation = arguments.get("operation")
        a = arguments.get("a")
        b = arguments.get("b")

        if operation is None or a is None:
            raise ValueError("operation and a are required")

        if operation != "sqrt" and b is None:
            raise ValueError(f"operation '{operation}' requires parameter 'b'")

        result = calculate(operation, a, b)

        # Format response
        if operation == "sqrt":
            text_response = f"√{a} = {result}"
        elif operation == "power":
            text_response = f"{a}^{b} = {result}"
        else:
            symbol_map = {"add": "+", "subtract": "-", "multiply": "×", "divide": "÷"}
            symbol = symbol_map.get(operation, operation)
            text_response = f"{a} {symbol} {b} = {result}"

        return [TextContent(type="text", text=text_response)]

    elif name == "factorial":
        n = arguments.get("n")
        if n is None:
            raise ValueError("n is required")

        if not isinstance(n, int):
            raise ValueError("n must be an integer")

        result = factorial(n)
        text_response = f"Factorial of {n} = {result}"

        return [TextContent(type="text", text=text_response)]

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
        "service": "math",
        "api_key_configured": MCP_API_KEY != "default-api-key"
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
