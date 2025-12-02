# Cloudflare Workers MCP Servers

This directory contains two MCP (Model Context Protocol) servers implemented as Cloudflare Workers using TypeScript.

## Overview

- **santa-clara**: Property tax information lookup by APN (Assessor's Parcel Number)
- **math**: Mathematical calculations and factorial computation

Both servers:
- Use TypeScript with full type safety
- Implement MCP JSON-RPC 2.0 protocol (version 2025-06-18)
- Include CORS support
- Require Bearer token authentication (API_KEY)
- Deploy to Cloudflare Workers for global edge distribution

## Architecture

### How It Works

```
User/Client
    ↓
curl/HTTP Request (with Bearer token)
    ↓
Cloudflare Workers (Global Edge)
    ↓
MCP Server (TypeScript)
    ↓
JSON-RPC 2.0 Response
```

### Why Cloudflare Workers?

- ✓ Global edge distribution (low latency)
- ✓ Serverless (no VMs to manage)
- ✓ Auto-scaling (handles traffic spikes)
- ✓ Free tier available
- ✓ Simple deployment with `wrangler`
- ✓ Built-in secrets management (API_KEY)

## Directory Structure

```
cloudflare-workers/
├── santa-clara/
│   ├── src/
│   │   └── index.ts          (MCP server implementation)
│   ├── wrangler.toml         (Cloudflare config)
│   ├── tsconfig.json         (TypeScript config)
│   ├── package.json          (Dependencies)
│   └── node_modules/         (npm packages)
│
├── math/
│   ├── src/
│   │   └── index.ts          (MCP server implementation)
│   ├── wrangler.toml         (Cloudflare config)
│   ├── tsconfig.json         (TypeScript config)
│   ├── package.json          (Dependencies)
│   └── node_modules/         (npm packages)
│
├── README.md                 (This file)
├── DEPLOYMENT.md             (Detailed deployment guide)
├── test-workers.sh           (Testing script)
└── ~/cloudflare-credentials/ (API keys - secure storage)
```

## Prerequisites

- Node.js 20.x or later
- Cloudflare account (free tier works)
- wrangler CLI installed globally: `npm install -g wrangler`

## Quick Start

### 1. Authenticate with Cloudflare

```bash
wrangler login
```

This opens a browser to authorize Wrangler with your Cloudflare account.

### 2. Deploy Workers

```bash
# Deploy santa-clara
cd ~/mcp-dev-environment/cloudflare-workers/santa-clara
wrangler deploy

# Deploy math
cd ../math
wrangler deploy
```

Both commands will output worker URLs like:
- `https://santa-clara.<account>.workers.dev`
- `https://math.<account>.workers.dev`

### 3. Set API Key Secrets

```bash
# For santa-clara
cd ../santa-clara
wrangler secret put API_KEY
# Paste: 6c2da9cf361a0d83b0306de7064cbd2fefceda59cdfe51ff300245f2cacf8ca9

# For math
cd ../math
wrangler secret put API_KEY
# Paste: 7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3
```

### 4. Test Workers

Use the provided test script:

```bash
cd ~/mcp-dev-environment/cloudflare-workers

./test-workers.sh \
  'https://santa-clara.your-account.workers.dev' \
  'https://math.your-account.workers.dev' \
  '6c2da9cf361a0d83b0306de7064cbd2fefceda59cdfe51ff300245f2cacf8ca9' \
  '7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3'
```

Or see [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed curl commands.

## Santa Clara Worker

### Tools

**get_property_info**
- Get property information by APN
- Input: `{"apn": "288-12-033"}`
- Output: Property details (address, owner, assessed value, tax amount, etc.)

### Example Request

```bash
curl -X POST "https://santa-clara.account.workers.dev" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 6c2da9cf361a0d83b0306de7064cbd2fefceda59cdfe51ff300245f2cacf8ca9" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_property_info",
      "arguments": {"apn": "288-12-033"}
    },
    "id": 1
  }'
```

## Math Worker

### Tools

**calculate**
- Perform basic mathematical operations
- Operations: add, subtract, multiply, divide, power, sqrt
- Input: `{"operation": "add", "a": 5, "b": 3}`

**factorial**
- Calculate factorial (0-100)
- Input: `{"n": 10}`

### Example Requests

```bash
# Addition: 5 + 3 = 8
curl -X POST "https://math.account.workers.dev" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "calculate",
      "arguments": {"operation": "add", "a": 5, "b": 3}
    },
    "id": 1
  }'

# Factorial: 10! = 3628800
curl -X POST "https://math.account.workers.dev" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "factorial",
      "arguments": {"n": 10}
    },
    "id": 2
  }'
```

## API Key Management

### Stored Keys

API keys are securely stored in:
- `~/cloudflare-credentials/santa-clara-api-key.txt`
- `~/cloudflare-credentials/math-api-key.txt`

### Cloudflare Storage

Once deployed, keys are encrypted in Cloudflare's secrets management:

```bash
# List secrets (encrypted, won't show actual values):
cd santa-clara
wrangler secret list

# Update a secret:
wrangler secret put API_KEY

# Delete a secret:
wrangler secret delete API_KEY
```

### Security Best Practices

1. ✓ Keys never stored in code or git
2. ✓ Keys encrypted at rest in Cloudflare
3. ✓ Keys only accessible to worker code
4. ✓ No way to retrieve stored secrets (by design)
5. ✓ Rotate keys periodically

## MCP Protocol Details

### Implemented Methods

**initialize**
```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "client", "version": "1.0"}
  },
  "id": 1
}
```

Response includes server info and protocol version.

**tools/list**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 2
}
```

Response includes available tools and their input schemas.

**tools/call**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {/* tool-specific args */}
  },
  "id": 3
}
```

Response includes tool results.

## Authentication

All endpoints require Bearer token authentication:

```bash
-H "Authorization: Bearer <API_KEY>"
```

### Error Response

Unauthorized request (missing or invalid token):

```json
{
  "error": "Unauthorized"
}
```

HTTP status: 401

## CORS Headers

Both workers support CORS:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

## Deployment Commands

### View all workers

```bash
wrangler list
```

### View worker logs (live tail)

```bash
cd santa-clara
wrangler tail
```

### Redeploy a worker

```bash
cd santa-clara
wrangler deploy
```

### Delete a worker

```bash
cd santa-clara
wrangler delete
```

⚠️ This is irreversible!

## Troubleshooting

### "Unauthorized" Errors

1. Verify API_KEY secret is set:
   ```bash
   wrangler secret put API_KEY
   ```

2. Verify Authorization header format:
   ```bash
   -H "Authorization: Bearer <YOUR_KEY>"
   ```

3. Verify you're using the correct key for each worker

### Worker Not Responding

1. Check worker deployment:
   ```bash
   wrangler list
   ```

2. View worker logs:
   ```bash
   wrangler tail
   ```

3. Verify the worker URL is correct

4. Check Cloudflare Workers dashboard for deployment errors

### "Command not found: wrangler"

Install globally or use npx:

```bash
# Global
npm install -g wrangler

# Or use npx
npx wrangler deploy
```

## Integration with Claude Desktop

HTTP-based MCP workers can be integrated with Claude Desktop, but require an adapter since Claude Desktop's native MCP support is primarily stdio-based.

See DEPLOYMENT.md for options and considerations.

## Comparison: Docker vs. Cloudflare Workers

| Feature | Docker (stdio) | Cloudflare Workers (HTTP) |
|---------|---|---|
| **Latency** | Local (~10ms) | Global (~100ms) |
| **Cost** | Free (local) | Free tier available |
| **Setup** | Local container | Cloud deployment |
| **Scaling** | Manual | Automatic |
| **Availability** | Requires running | Always on |
| **Use Case** | Development | Production |

## Development

### Local Development Mode

```bash
cd santa-clara
wrangler dev
```

This starts a local server at `http://localhost:8787` for testing before deployment.

### Modifying Workers

1. Edit `src/index.ts`
2. TypeScript is compiled automatically
3. Redeploy with `wrangler deploy`

### Testing During Development

```bash
wrangler dev
# Then in another terminal:
curl -X POST "http://localhost:8787" ...
```

## Performance

- **Response time**: ~50-100ms (including network)
- **Concurrent requests**: Unlimited (Cloudflare auto-scales)
- **Data transfer**: Included in free tier

## Monitoring

View real-time logs:

```bash
cd santa-clara
wrangler tail
```

View metrics in Cloudflare dashboard:
- Requests per minute
- Error rates
- Response times
- CPU time

## References

- [Cloudflare Workers Docs](https://developers.cloudflare.com/workers/)
- [Wrangler CLI Guide](https://developers.cloudflare.com/workers/wrangler/)
- [MCP Specification](https://modelcontextprotocol.io/)

## Support

For issues or questions:

1. Check DEPLOYMENT.md for deployment troubleshooting
2. Review wrangler logs: `wrangler tail`
3. Check Cloudflare Workers dashboard
4. See troubleshooting section in this file
