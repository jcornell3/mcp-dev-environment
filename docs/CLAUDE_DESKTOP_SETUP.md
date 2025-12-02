# Claude Desktop MCP Configuration Setup

This guide covers setting up Claude Desktop to use all 4 MCP servers: 2 local (Docker-based) and 2 cloud (Cloudflare Workers).

## Overview

| Server | Type | Location | Latency | Status |
|--------|------|----------|---------|--------|
| **santa-clara-local** | stdio | Docker container | ~10ms | Requires docker running |
| **math-local** | stdio | Docker container | ~10ms | Requires docker running |
| **santa-clara-cloud** | HTTP | Cloudflare edge | ~100-150ms | Always available |
| **math-cloud** | HTTP | Cloudflare edge | ~100-150ms | Always available |

## Installation

### Step 1: Get the Configuration File

The combined configuration is in:
```
~/mcp-dev-environment/claude_desktop_config_COMBINED.json
```

### Step 2: Copy to Claude Desktop Config Directory

Choose your platform:

#### Windows (WSL2 setup)
```bash
# From WSL or PowerShell
copy %USERPROFILE%\...\claude_desktop_config_COMBINED.json ^
      %APPDATA%\Claude\claude_desktop_config.json
```

Or manually:
1. Open File Explorer: `C:\Users\<YOUR-USERNAME>\AppData\Roaming\Claude\`
2. Copy `claude_desktop_config_COMBINED.json` from your project folder
3. Rename to `claude_desktop_config.json`
4. Replace existing file if prompted

**Exact path:** `C:\Users\<YOUR-USERNAME>\AppData\Roaming\Claude\claude_desktop_config.json`

#### macOS
```bash
cp ~/mcp-dev-environment/claude_desktop_config_COMBINED.json \
   "~/Library/Application Support/Claude/claude_desktop_config.json"
```

**Exact path:** `~/Library/Application Support/Claude/claude_desktop_config.json`

#### Linux
```bash
cp ~/mcp-dev-environment/claude_desktop_config_COMBINED.json \
   ~/.config/Claude/claude_desktop_config.json
```

**Exact path:** `~/.config/Claude/claude_desktop_config.json`

### Step 3: Restart Claude Desktop

Close Claude Desktop completely and reopen it. The MCP servers should now be available.

## Configuration Details

### Local Servers (Docker-based)

**Container Requirements:**
- Docker Desktop must be running
- Containers must be running: `docker compose up -d`
- Transport: stdio (binary, fast)

**Santa Clara Local:**
- Command: `wsl docker exec -i mcp-dev-environment-santa-clara-1 python -u /app/server.py`
- Tool: `get_property_info` - Property tax lookup by APN
- Response time: ~10ms

**Math Local:**
- Command: `wsl docker exec -i mcp-dev-environment-math-1 python -u /app/server.py`
- Tools: `calculate`, `factorial`
- Response time: ~10ms

### Cloud Servers (Cloudflare Workers)

**No Setup Required:**
- Always available globally
- No local services to run
- Transport: HTTP via curl (text-based)

**Santa Clara Cloud:**
- URL: `https://santa-clara.tamshai.workers.dev`
- Tool: `get_property_info` - Property tax lookup by APN
- API Key: `6c2da9cf361a0d83b0306de7064cbd2fefceda59cdfe51ff300245f2cacf8ca9`
- Response time: ~100-150ms

**Math Cloud:**
- URL: `https://math.tamshai.workers.dev`
- Tools: `calculate`, `factorial`
- API Key: `7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3`
- Response time: ~100-150ms

## When to Use Each Server

### Use Local Servers When:
- ✅ Developing MCP tools locally
- ✅ Testing changes before cloud deployment
- ✅ Need fast response times (~10ms)
- ✅ Offline development (no internet required)
- ✅ Running tests frequently

**Prerequisites:**
```bash
# Start Docker containers
docker compose up -d

# Verify they're running
docker compose ps

# Logs
docker compose logs -f santa-clara
docker compose logs -f math
```

### Use Cloud Servers When:
- ✅ Demonstrating stable functionality
- ✅ Sharing with others (no local setup required)
- ✅ Need high availability (99.95% SLA)
- ✅ Offline, can't run Docker
- ✅ Production use

**No setup required** - just use in Claude Desktop.

## Testing Each Server

### Verify Configuration is Loaded

After restarting Claude Desktop:
1. Open Claude Desktop
2. Check the tool/file picker (if available)
3. You should see all 4 servers listed

### Test Santa Clara Local

In Claude Desktop, ask:
```
Use the santa-clara-local server to get property info for APN 288-12-033
```

Expected response time: ~10ms

### Test Math Local

In Claude Desktop, ask:
```
Use the math-local server to calculate 5 + 3
```

Or:
```
Use the math-local server to calculate factorial of 10
```

Expected response time: ~10ms

### Test Santa Clara Cloud

In Claude Desktop, ask:
```
Use the santa-clara-cloud server to get property info for APN 288-12-033
```

Expected response time: ~100-150ms

### Test Math Cloud

In Claude Desktop, ask:
```
Use the math-cloud server to calculate 5 + 3
```

Or:
```
Use the math-cloud server to calculate factorial of 10
```

Expected response time: ~100-150ms

### Manual Testing (if needed)

**Test Local Santa Clara:**
```bash
# Get container name
docker compose ps | grep santa-clara

# Execute test
docker exec -i mcp-dev-environment-santa-clara-1 python -u /app/server.py <<'EOF'
{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}
EOF
```

**Test Cloud Santa Clara:**
```bash
curl -X POST "https://santa-clara.tamshai.workers.dev" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 6c2da9cf361a0d83b0306de7064cbd2fefceda59cdfe51ff300245f2cacf8ca9" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

**Test Local Math:**
```bash
docker exec -i mcp-dev-environment-math-1 python -u /app/server.py <<'EOF'
{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}
EOF
```

**Test Cloud Math:**
```bash
curl -X POST "https://math.tamshai.workers.dev" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

## Troubleshooting

### Claude Desktop Not Showing Any Tools

**Check Configuration File:**
```bash
# Verify the file exists
ls -la ~/.config/Claude/claude_desktop_config.json  # Linux
ls -la "~/Library/Application Support/Claude/claude_desktop_config.json"  # macOS
dir "%APPDATA%\Claude\claude_desktop_config.json"  # Windows

# Verify JSON syntax
jq . ~/.config/Claude/claude_desktop_config.json
```

**Solution:** Restart Claude Desktop after copying the configuration file.

### Local Servers Not Working

**Error:** "Connection refused" or "docker: command not found"

**Fix:**
```bash
# Start Docker containers
docker compose up -d

# Verify they're running
docker compose ps

# Check logs
docker compose logs santa-clara
docker compose logs math
```

**Check WSL integration (Windows):**
```bash
# In PowerShell
wsl --list --verbose

# Should show docker and wsl integration enabled
```

### Cloud Servers Returning 401 Unauthorized

**Error:** `{"error": "Unauthorized"}`

**Fix:** API keys in the config may have changed. Update them:

**Santa Clara Cloud Key:**
```
6c2da9cf361a0d83b0306de7064cbd2fefceda59cdfe51ff300245f2cacf8ca9
```

**Math Cloud Key:**
```
7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3
```

Edit `claude_desktop_config.json` and verify these keys are correct in the Authorization headers.

### Slow Responses from Local Servers

**Symptom:** Local servers taking 100ms+

**Check Docker resources:**
```bash
# Check container status
docker compose ps

# Check resource usage
docker stats

# Restart if needed
docker compose restart
```

### Slow Responses from Cloud Servers

**Expected:** Cloud servers normally respond in 100-150ms due to:
- Network latency to Cloudflare edge
- Server processing time
- Geographic distance

This is normal. If responses exceed 5 seconds, check:
```bash
# Test directly
curl -w "\nTotal time: %{time_total}s\n" -X POST "https://santa-clara.tamshai.workers.dev" ...

# Check Cloudflare dashboard for worker status
```

### Configuration Not Updating After Restart

**Solution:**
1. Close Claude Desktop completely
2. Wait 5 seconds
3. Verify the config file was copied correctly
4. Reopen Claude Desktop

**Check the file was copied to correct location:**
```bash
# macOS
cat "~/Library/Application Support/Claude/claude_desktop_config.json"

# Linux
cat ~/.config/Claude/claude_desktop_config.json

# Windows PowerShell
type $env:APPDATA\Claude\claude_desktop_config.json
```

## Advanced Configuration

### Using Only Cloud Servers

If you don't want to run Docker locally, create a minimal config:

```json
{
  "mcpServers": {
    "santa-clara-cloud": { /* santa-clara-cloud config */ },
    "math-cloud": { /* math-cloud config */ }
  }
}
```

### Using Only Local Servers

If you prefer local-only development:

```json
{
  "mcpServers": {
    "santa-clara-local": { /* santa-clara-local config */ },
    "math-local": { /* math-local config */ }
  }
}
```

### Adding Custom Servers

You can add additional MCP servers to this config:

```json
{
  "mcpServers": {
    "my-custom-server": {
      "command": "python",
      "args": ["/path/to/server.py"]
    },
    /* ... rest of config ... */
  }
}
```

## Performance Comparison

| Aspect | Local | Cloud |
|--------|-------|-------|
| **Latency** | ~10ms | ~100-150ms |
| **Availability** | Requires Docker | Always on (99.95% SLA) |
| **Setup** | docker compose up | None |
| **Cost** | Free | Free tier (100k req/day) |
| **Best For** | Development | Production/Demo |

## References

- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Claude Desktop Documentation](https://claude.ai/docs)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)

## Support

For issues:
1. Check this troubleshooting section
2. Review server logs: `docker compose logs`
3. Check Cloudflare dashboard for cloud worker status
4. Verify configuration file syntax with `jq`

---

**Last Updated:** 2025-12-01

**Status:** Production Ready
- ✅ 4 MCP servers configured
- ✅ 2 local (stdio) + 2 cloud (HTTP)
- ✅ All tests passing
- ✅ Ready for Claude Desktop integration
