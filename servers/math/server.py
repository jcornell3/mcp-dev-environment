#!/usr/bin/env python3
"""
Math Operations MCP Server
Uses MCP Python SDK with stdio transport for Claude Desktop integration
Provides mathematical calculation and factorial tools
"""

import asyncio
import sys
import math
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


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


async def main():
    """Run the MCP server using stdio transport"""
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
