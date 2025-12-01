#!/usr/bin/env python3
"""
Santa Clara Property Tax MCP Server
Uses MCP Python SDK with stdio transport for Claude Desktop integration
"""

import asyncio
import sys
from datetime import datetime
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Initialize MCP server
server = Server("santa-clara")


def generate_property_data(apn: str) -> dict:
    """Generate realistic mock property data based on APN"""
    hash_val = sum(ord(c) for c in apn) % 10000

    property_types = ["residential", "commercial", "industrial", "mixed-use"]
    street_names = ["Main Street", "Oak Avenue", "Park Boulevard", "Broadway"]

    return {
        "apn": apn,
        "address": f"{1000 + hash_val} {street_names[hash_val % 4]}, Santa Clara, CA 95050",
        "owner": {
            "name": f"Property Owner {hash_val % 100}",
            "type": "corporation" if hash_val % 2 == 0 else "individual"
        },
        "property_type": property_types[hash_val % 4],
        "assessed_value": 500000 + (hash_val * 1000),
        "tax_amount": (500000 + (hash_val * 1000)) * 0.012,
        "year_built": 1950 + (hash_val % 75),
        "lot_size_sqft": 5000 + (hash_val * 100),
        "building_sqft": 1500 + (hash_val * 50),
        "bedrooms": 2 + (hash_val % 4),
        "bathrooms": 1 + (hash_val % 3),
        "last_sale_date": "2020-01-01",
        "last_sale_price": 450000 + (hash_val * 1000),
        "status": "active",
        "county": "Santa Clara",
        "land_use_code": "R1" if property_types[hash_val % 4] == "residential" else "C2",
        "parcel_number": apn,
        "retrieved_at": datetime.now().isoformat()
    }


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
