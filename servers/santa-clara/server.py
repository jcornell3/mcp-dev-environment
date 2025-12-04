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
