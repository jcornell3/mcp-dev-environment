# Cloudflare Workers MCP Servers - Deployment Guide

## API Keys (Generated)

**Santa Clara Worker:**
```
6c2da9cf361a0d83b0306de7064cbd2fefceda59cdfe51ff300245f2cacf8ca9
```

**Math Worker:**
```
7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3
```

⚠️ **IMPORTANT**: Store these keys securely. You'll need them to:
1. Configure Cloudflare Worker secrets
2. Make requests to the workers (Authorization header)

---

## Step 1: Cloudflare Authentication

Before deploying, authenticate with Cloudflare:

```bash
wrangler login
```

This will:
1. Open a browser to login.cloudflare.com
2. Ask you to authorize Wrangler
3. Return you to the terminal when complete

Verify authentication:
```bash
wrangler whoami
```

Expected output: Your Cloudflare email address

---

## Step 2: Deploy Santa Clara Worker

From the santa-clara directory:

```bash
cd ~/mcp-dev-environment/cloudflare-workers/santa-clara
wrangler deploy
```

This will:
1. Compile TypeScript to JavaScript
2. Bundle the code
3. Deploy to Cloudflare Workers
4. Output a worker URL like: `https://santa-clara.<YOUR-ACCOUNT>.workers.dev`

**SAVE THIS URL** - You'll need it for testing and Claude Desktop configuration.

Example output:
```
 ⛅️ wrangler 4.51.0
───────────────────
✓ Deployed santa-clara worker (12.34 sec)

https://santa-clara.your-account.workers.dev
```

---

## Step 3: Deploy Math Worker

From the math directory:

```bash
cd ~/mcp-dev-environment/cloudflare-workers/math
wrangler deploy
```

Same process as santa-clara. **SAVE THE WORKER URL**.

---

## Step 4: Configure API Key Secrets

After deploying, set the API_KEY secret for each worker.

### Santa Clara Secret:

```bash
cd ~/mcp-dev-environment/cloudflare-workers/santa-clara
wrangler secret put API_KEY
```

When prompted for the secret value, paste:
```
6c2da9cf361a0d83b0306de7064cbd2fefceda59cdfe51ff300245f2cacf8ca9
```

### Math Secret:

```bash
cd ~/mcp-dev-environment/cloudflare-workers/math
wrangler secret put API_KEY
```

When prompted for the secret value, paste:
```
7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3
```

---

## Step 5: Test Workers with curl

Replace the URLs and API keys with your actual values from deployment.

### Test Santa Clara Worker

```bash
# Set variables
SANTA_CLARA_URL="https://santa-clara.your-account.workers.dev"
SANTA_CLARA_KEY="6c2da9cf361a0d83b0306de7064cbd2fefceda59cdfe51ff300245f2cacf8ca9"

# Test 1: Initialize
echo "Testing initialize..."
curl -X POST "$SANTA_CLARA_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SANTA_CLARA_KEY" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'

# Test 2: List Tools
echo ""
echo "Testing tools/list..."
curl -X POST "$SANTA_CLARA_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SANTA_CLARA_KEY" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2}'

# Test 3: Get Property Info
echo ""
echo "Testing tools/call (get_property_info)..."
curl -X POST "$SANTA_CLARA_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SANTA_CLARA_KEY" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_property_info","arguments":{"apn":"288-12-033"}},"id":3}'
```

### Test Math Worker

```bash
# Set variables
MATH_URL="https://math.your-account.workers.dev"
MATH_KEY="7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3"

# Test 1: Initialize
echo "Testing initialize..."
curl -X POST "$MATH_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MATH_KEY" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'

# Test 2: List Tools
echo ""
echo "Testing tools/list..."
curl -X POST "$MATH_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MATH_KEY" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2}'

# Test 3: Calculate (Add)
echo ""
echo "Testing tools/call (calculate add)..."
curl -X POST "$MATH_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MATH_KEY" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"calculate","arguments":{"operation":"add","a":5,"b":3}},"id":3}'

# Test 4: Factorial
echo ""
echo "Testing tools/call (factorial)..."
curl -X POST "$MATH_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MATH_KEY" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"factorial","arguments":{"n":10}},"id":4}'
```

---

## Step 6: Configure Claude Desktop

Once workers are deployed and tested, update your Claude Desktop configuration to use the HTTP endpoints.

### Claude Desktop Config Location:

- **Windows**: `C:\Users\<YOUR-USERNAME>\AppData\Roaming\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Configuration Example:

```json
{
  "mcpServers": {
    "santa-clara-cloudflare": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "https://santa-clara.your-account.workers.dev",
        "-H", "Content-Type: application/json",
        "-H", "Authorization: Bearer 6c2da9cf361a0d83b0306de7064cbd2fefceda59cdfe51ff300245f2cacf8ca9"
      ]
    },
    "math-cloudflare": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "https://math.your-account.workers.dev",
        "-H", "Content-Type: application/json",
        "-H", "Authorization: Bearer 7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3"
      ]
    }
  }
}
```

⚠️ **Note**: Claude Desktop doesn't directly support `curl` in this way. For HTTP-based MCP, you'll need to use a wrapper or adapter. See troubleshooting below.

---

## Troubleshooting

### "wrangler: command not found"
Wrangler is installed locally in each worker directory. Use:
```bash
npx wrangler login
npx wrangler deploy
```

### "401 Unauthorized" when testing
- Verify the API_KEY secret was set correctly with `wrangler secret put API_KEY`
- Verify the Authorization header uses correct format: `Bearer <API_KEY>`
- Check that API key matches what was deployed

### "Worker not responding"
- Verify worker is deployed: Check Cloudflare Workers dashboard
- Check worker logs: `wrangler tail` (shows live logs)
- Verify the worker URL is correct (check deployment output)

### Claude Desktop Integration Issues
HTTP-based MCP requires a different approach than stdio. Options:
1. Use a local HTTP proxy (like wrangler `dev` mode)
2. Use an adapter tool
3. Keep Docker stdio-based for local development, use Cloudflare for cloud

---

## Useful Commands

### View deployed workers:
```bash
wrangler list
```

### View worker logs:
```bash
cd ~/mcp-dev-environment/cloudflare-workers/santa-clara
wrangler tail
```

### Retrieve stored secrets:
```bash
# Secrets are encrypted and can't be retrieved, only updated
# This will fail intentionally for security:
wrangler secret list
```

### Delete/redeploy a worker:
```bash
cd ~/mcp-dev-environment/cloudflare-workers/santa-clara
wrangler publish  # Redeploy current code
wrangler delete   # Remove worker (irreversible!)
```

---

## Summary

| Component | Status | Details |
|-----------|--------|---------|
| API Keys | ✓ Generated | Stored in ~/cloudflare-credentials/ |
| Workers Code | ✓ Ready | TypeScript, fully typed, MCP 2.0 |
| Deployment | ⏳ Pending | Requires `wrangler login` and `wrangler deploy` |
| Testing | ⏳ Pending | curl commands provided above |
| Claude Desktop | ⏳ To implement | Requires HTTP adapter or stdio wrapper |

---

## Next Steps

1. Run `wrangler login` in a terminal with browser access
2. Deploy both workers using provided commands
3. Set API_KEY secrets for each worker
4. Test with curl commands provided above
5. Implement Claude Desktop integration (HTTP adapter needed)
