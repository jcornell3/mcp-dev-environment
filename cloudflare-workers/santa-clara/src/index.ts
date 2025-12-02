/**
 * Santa Clara Property Tax MCP Server
 * Cloudflare Worker Implementation
 */

interface Env {
  API_KEY: string;
}

interface MCPRequest {
  jsonrpc: string;
  method: string;
  params?: any;
  id: number | string;
}

interface MCPResponse {
  jsonrpc: string;
  id: number | string;
  result?: any;
  error?: any;
}

// Generate mock property data
function generatePropertyData(apn: string): any {
  const hashVal = apn.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);

  const propertyTypes = ["residential", "commercial", "industrial", "mixed-use"];
  const streetNames = ["Main Street", "Oak Avenue", "Park Boulevard", "Broadway"];

  return {
    apn: apn,
    address: `${1000 + (hashVal % 9000)} ${streetNames[hashVal % 4]}, Santa Clara, CA 95050`,
    owner: {
      name: `Property Owner ${hashVal % 100}`,
      type: hashVal % 2 === 0 ? "corporation" : "individual"
    },
    property_type: propertyTypes[hashVal % 4],
    assessed_value: 500000 + (hashVal % 10000000),
    tax_amount: (500000 + (hashVal % 10000000)) * 0.012,
    year_built: 1950 + (hashVal % 75),
    lot_size_sqft: 5000 + (hashVal % 50000),
    building_sqft: 1500 + (hashVal % 10000),
    bedrooms: 2 + (hashVal % 4),
    bathrooms: 1 + (hashVal % 3),
    last_sale_date: "2020-01-01",
    last_sale_price: 450000 + (hashVal % 5000000),
    status: "active",
    county: "Santa Clara",
    land_use_code: propertyTypes[hashVal % 4] === "residential" ? "R1" : "C2",
    parcel_number: apn,
    retrieved_at: new Date().toISOString()
  };
}

function formatPropertyText(data: any): string {
  return `Property Information for APN: ${data.apn}

Address: ${data.address}
Owner: ${data.owner.name}
Property Type: ${data.property_type}
Assessed Value: $${data.assessed_value.toLocaleString()}
Tax Amount: $${Math.round(data.tax_amount).toLocaleString()}
Year Built: ${data.year_built}
Lot Size: ${data.lot_size_sqft.toLocaleString()} sqft
Building Size: ${data.building_sqft.toLocaleString()} sqft`;
}

function handleInitialize(id: number | string): MCPResponse {
  return {
    jsonrpc: "2.0",
    id: id,
    result: {
      protocolVersion: "2025-06-18",
      capabilities: {},
      serverInfo: {
        name: "santa-clara",
        version: "1.0.0"
      }
    }
  };
}

function handleToolsList(id: number | string): MCPResponse {
  return {
    jsonrpc: "2.0",
    id: id,
    result: {
      tools: [
        {
          name: "get_property_info",
          description: "Get property information by APN (Assessor's Parcel Number)",
          inputSchema: {
            type: "object",
            properties: {
              apn: {
                type: "string",
                description: "Property APN (Assessor's Parcel Number), e.g., '123-456-789'"
              }
            },
            required: ["apn"]
          }
        }
      ]
    }
  };
}

function handleToolsCall(params: any, id: number | string): MCPResponse {
  const toolName = params.name;
  const args = params.arguments || {};

  if (toolName === "get_property_info") {
    const apn = args.apn;

    if (!apn) {
      return {
        jsonrpc: "2.0",
        id: id,
        error: {
          code: -32602,
          message: "APN is required"
        }
      };
    }

    const data = generatePropertyData(apn);
    const text = formatPropertyText(data);

    return {
      jsonrpc: "2.0",
      id: id,
      result: {
        content: [
          {
            type: "text",
            text: text
          }
        ]
      }
    };
  }

  return {
    jsonrpc: "2.0",
    id: id,
    error: {
      code: -32601,
      message: `Unknown tool: ${toolName}`
    }
  };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    };

    // Handle OPTIONS (CORS preflight)
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // Only accept POST requests
    if (request.method !== 'POST') {
      return new Response('Method not allowed', {
        status: 405,
        headers: corsHeaders
      });
    }

    // Check authentication
    const authHeader = request.headers.get('Authorization');
    const expectedAuth = `Bearer ${env.API_KEY}`;

    if (authHeader !== expectedAuth) {
      return new Response(JSON.stringify({
        error: 'Unauthorized'
      }), {
        status: 401,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      });
    }

    // Parse JSON-RPC request
    let mcpRequest: MCPRequest;
    try {
      mcpRequest = await request.json() as MCPRequest;
    } catch (e) {
      return new Response(JSON.stringify({
        jsonrpc: "2.0",
        id: null,
        error: {
          code: -32700,
          message: "Parse error"
        }
      }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      });
    }

    // Handle MCP methods
    let response: MCPResponse;

    switch (mcpRequest.method) {
      case 'initialize':
        response = handleInitialize(mcpRequest.id);
        break;

      case 'tools/list':
        response = handleToolsList(mcpRequest.id);
        break;

      case 'tools/call':
        response = handleToolsCall(mcpRequest.params, mcpRequest.id);
        break;

      default:
        response = {
          jsonrpc: "2.0",
          id: mcpRequest.id,
          error: {
            code: -32601,
            message: `Method not found: ${mcpRequest.method}`
          }
        };
    }

    return new Response(JSON.stringify(response), {
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders
      }
    });
  }
};
