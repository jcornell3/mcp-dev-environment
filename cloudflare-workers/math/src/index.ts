/**
 * Math MCP Server
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

function handleInitialize(id: number | string): MCPResponse {
  return {
    jsonrpc: "2.0",
    id: id,
    result: {
      protocolVersion: "2025-06-18",
      capabilities: {},
      serverInfo: {
        name: "math",
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
          name: "calculate",
          description: "Perform basic mathematical calculations",
          inputSchema: {
            type: "object",
            properties: {
              operation: {
                type: "string",
                enum: ["add", "subtract", "multiply", "divide", "power", "sqrt"],
                description: "Mathematical operation to perform"
              },
              a: {
                type: "number",
                description: "First number"
              },
              b: {
                type: "number",
                description: "Second number (not needed for sqrt)"
              }
            },
            required: ["operation", "a"]
          }
        },
        {
          name: "factorial",
          description: "Calculate factorial of a number",
          inputSchema: {
            type: "object",
            properties: {
              n: {
                type: "integer",
                minimum: 0,
                maximum: 100,
                description: "Number to calculate factorial for (0-100)"
              }
            },
            required: ["n"]
          }
        }
      ]
    }
  };
}

function factorial(n: number): number {
  if (n === 0 || n === 1) return 1;
  let result = 1;
  for (let i = 2; i <= n; i++) {
    result *= i;
  }
  return result;
}

function handleToolsCall(params: any, id: number | string): MCPResponse {
  const toolName = params.name;
  const args = params.arguments || {};

  if (toolName === "calculate") {
    const operation = args.operation;
    const a = parseFloat(args.a);
    const b = parseFloat(args.b || 0);

    let result: number;
    let text: string;

    try {
      switch (operation) {
        case "add":
          result = a + b;
          text = `Result: ${a} + ${b} = ${result}`;
          break;
        case "subtract":
          result = a - b;
          text = `Result: ${a} - ${b} = ${result}`;
          break;
        case "multiply":
          result = a * b;
          text = `Result: ${a} × ${b} = ${result}`;
          break;
        case "divide":
          if (b === 0) {
            throw new Error("Cannot divide by zero");
          }
          result = a / b;
          text = `Result: ${a} ÷ ${b} = ${result}`;
          break;
        case "power":
          result = Math.pow(a, b);
          text = `Result: ${a}^${b} = ${result}`;
          break;
        case "sqrt":
          if (a < 0) {
            throw new Error("Cannot take square root of negative number");
          }
          result = Math.sqrt(a);
          text = `Result: √${a} = ${result}`;
          break;
        default:
          throw new Error(`Unknown operation: ${operation}`);
      }

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
    } catch (e: any) {
      return {
        jsonrpc: "2.0",
        id: id,
        error: {
          code: -32602,
          message: e.message
        }
      };
    }
  }

  if (toolName === "factorial") {
    const n = parseInt(args.n);

    if (isNaN(n) || n < 0 || n > 100) {
      return {
        jsonrpc: "2.0",
        id: id,
        error: {
          code: -32602,
          message: "Factorial only supported for 0-100"
        }
      };
    }

    const result = factorial(n);

    return {
      jsonrpc: "2.0",
      id: id,
      result: {
        content: [
          {
            type: "text",
            text: `Factorial of ${n} = ${result}`
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
