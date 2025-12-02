# MCP Development - Lessons Learned

**Date:** December 1, 2025  
**Project:** MCP Development Environment Setup  
**Status:** Phase 3 Complete - Working MCP Server Integrated with Claude Desktop  

---

## Executive Summary

This document captures all critical lessons learned from setting up a complete MCP development environment from scratch, building an MCP server, and integrating it with Claude Desktop. These lessons will save hours of troubleshooting for future developers.

---

## Critical Discovery: MCP Protocol Requirements

### **The Fundamental Mistake**

**Initial Approach (WRONG):**
- Built Flask HTTP server
- Created nginx reverse proxy
- Used curl wrapper script for stdio communication

**Why it failed:**
- Curl wrapper exits after single request
- Cannot maintain persistent stdio connection
- MCP protocol requires bidirectional, persistent stdio communication
- Multiple JSON-RPC messages must be handled sequentially

### **Correct Approach:**

**Use MCP Python SDK with stdio transport:**
```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
```

**Key Requirements:**
1. ✅ Server stays running (doesn't exit after one request)
2. ✅ Reads JSON-RPC messages line-by-line from stdin
3. ✅ Writes responses line-by-line to stdout
4. ✅ Handles initialize, tools/list, tools/call, and other MCP methods
5. ✅ Uses correct protocol version (2025-06-18 for Claude Desktop)

---

## Phase 2: Environment Setup - Issues & Solutions

### **Issue 1: Missing nginx Config File**

**Problem:** Copilot created docker-compose.yml but not nginx/conf.d/mcp-servers.conf

**Root Cause:** Incomplete initial setup prompt

**Solution:** 
- Add explicit requirement to create nginx/conf.d/mcp-servers.conf
- Include actual route configurations, not just placeholders
- Verify all files exist before proceeding

**Prevention:** Updated FRESH_WORKSTATION_SETUP.md with complete file list

---

### **Issue 2: Certificate Naming Mismatch**

**Problem:** mkcert created `localhost+2.pem` but docker-compose expected `localhost.pem`

**Root Cause:** mkcert default naming convention vs. our expected names

**Solution:** Use explicit flags:
```bash
mkcert -cert-file certs/localhost.pem -key-file certs/localhost-key.pem localhost 127.0.0.1 ::1
```

**Prevention:** Added explicit flags to setup instructions

---

### **Issue 3: Placeholder vs. Working Code**

**Problem:** Initial santa-clara server was Flask demo, not actual MCP server

**Root Cause:** Setup prompt didn't emphasize "working implementation"

**Solution:** Explicitly require:
- Actual MCP protocol implementation
- Real endpoint handlers (/mcp, not just /)
- Working tools with mock data

**Prevention:** Updated prompt with "Create actual working MCP server code, not just placeholders"

---

### **Issue 4: GitHub Username Guessing**

**Problem:** Copilot guessed GitHub username as "USERNAME" (wrong - actual: USERNAME)

**Root Cause:** AI inference without verification

**Solution:** 
- Always verify remote URL: `git remote -v`
- Correct immediately if wrong
- Use full GitHub URLs in prompts

**Prevention:** Added verification step to Git push workflow

---

### **Issue 5: Terminal Instability in VS Code WSL**

**Problem:** Long-running docker commands caused terminal crashes (exit codes 1, 2, 130)

**Root Cause:** VS Code terminal handling of streaming output in WSL

**Solution:** 
- Use file-based diagnostics: save outputs to logs/diagnostics/
- Add `--verbose` flags to hung commands
- Press Ctrl+C and retry (normal behavior)
- Use shorter commands when possible

**Prevention:** 
- Documented as normal behavior
- Added troubleshooting section
- Explained how to recover

---

## Phase 3: Claude Desktop Integration - Critical Issues

### **Issue 1: HTTP/Curl Wrapper Approach Fails**

**Problem:** curl-based wrapper showed in tools list but couldn't execute tools

**Symptoms:**
- `tools/list` worked
- `tools/call` timed out or failed
- "Tool not found" errors
- 60-second timeouts

**Root Cause:** 
- Curl wrapper exits after one request
- Cannot handle multiple JSON-RPC messages over same stdio connection
- MCP protocol requires persistent bidirectional communication

**Debug Evidence from wrapper-debug.log:**
```
INPUT:
{"method":"initialize",...}
{"jsonrpc":"2.0","method":"notifications/cancelled",...}
```

Two JSON objects sent, but curl only processes first and exits.

**Solution:** Abandon HTTP approach entirely, use MCP Python SDK

---

### **Issue 2: Protocol Version Mismatch**

**Problem:** Server returned `"protocolVersion": "2024-11-05"` but Claude Desktop expected `"2025-06-18"`

**Symptoms:**
- Initialize requests timed out after 60 seconds
- Claude Desktop rejected responses silently

**Solution:** Match Claude Desktop's protocol version exactly

**Verification:**
```bash
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18",...},"id":1}' | test-command
```

Response must include: `"protocolVersion": "2025-06-18"`

---

### **Issue 3: Container Name Mismatch**

**Problem:** Config used `santa-clara-1` but actual container: `mcp-dev-environment-santa-clara-1`

**Error:** `Error response from daemon: No such container: santa-clara-1`

**Root Cause:** docker-compose project name prefix not accounted for

**Solution:** 
```bash
# Get actual name
docker compose ps

# Use full name in config
"mcp-dev-environment-santa-clara-1"
```

**Prevention:** Always verify container names with `docker compose ps`

---

### **Issue 4: Config File Location Confusion**

**Problem:** Claude Code created config in WSL filesystem (`~/...`) instead of Windows filesystem

**Correct Location:** `C:\Users\USERNAME\AppData\Roaming\Claude\claude_desktop_config.json`

**Solution:** Explicitly specify Windows path, not WSL path

---

### **Issue 5: Command Invocation from Windows**

**Problem:** Config used `"command": "docker"` which doesn't work from Windows

**Solution:** Use `"command": "wsl"` to invoke WSL commands from Windows

**Working Config:**
```json
{
  "mcpServers": {
    "santa-clara-local": {
      "command": "wsl",
      "args": [
        "docker",
        "exec",
        "-i",
        "mcp-dev-environment-santa-clara-1",
        "python",
        "-u",
        "/app/server.py"
      ]
    }
  }
}
```

---

## MCP Python SDK: What We Learned

### **Correct Server Structure**

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("santa-clara")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [Tool(name="...", description="...", inputSchema={...})]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    return [TextContent(type="text", text="...")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

### **Key Requirements:**

1. **Server Name:** Used in serverInfo response
2. **Decorators:** `@app.list_tools()` and `@app.call_tool()`
3. **Return Types:** Must match MCP spec exactly
4. **Async/Await:** All handlers must be async
5. **stdio_server:** Handles stdin/stdout communication properly
6. **Persistent:** Server runs indefinitely via asyncio event loop

---

## Docker Configuration for MCP Servers

### **Dockerfile Requirements**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
RUN chmod +x server.py

# CRITICAL: Use -u flag for unbuffered output
CMD ["python", "-u", "server.py"]
```

**Key Points:**
- `-u` flag: Unbuffered output (critical for stdio)
- No HTTP server needed (no Flask, Gunicorn, etc.)
- Lightweight image (python:slim)

### **requirements.txt**

```
mcp>=1.0.0
```

That's it! No Flask, no gunicorn, no HTTP dependencies.

---

## Testing MCP Servers

### **Test Initialize**

```bash
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | docker exec -i CONTAINER_NAME python -u /app/server.py
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "serverInfo": {"name": "santa-clara", "version": "1.0"}
  }
}
```

### **Test Tools/List**

```bash
echo '{"jsonrpc":"2.0","method":"tools/list","id":2}' | docker exec -i CONTAINER_NAME python -u /app/server.py
```

### **Test Tools/Call**

```bash
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_property_info","arguments":{"apn":"123-456-789"}},"id":3}' | docker exec -i CONTAINER_NAME python -u /app/server.py
```

**Response Time:** Should be < 100ms for all methods

---

## Claude Desktop Integration Checklist

### **Before Connecting:**

- [ ] MCP server implements stdio transport (not HTTP)
- [ ] Container is running: `docker compose ps`
- [ ] Get exact container name: `docker compose ps | grep santa-clara`
- [ ] Test initialize manually (as shown above)
- [ ] Test tools/list manually
- [ ] Test tools/call manually
- [ ] Verify protocol version is 2025-06-18

### **Config File:**

- [ ] Location: `C:\Users\USERNAME\AppData\Roaming\Claude\claude_desktop_config.json`
- [ ] Command: `"wsl"` (not `"docker"` or `"bash"`)
- [ ] Container name: Full name with project prefix
- [ ] Python unbuffered: `-u` flag present
- [ ] Valid JSON syntax (use validator)

### **After Config Update:**

- [ ] Restart Claude Desktop completely
- [ ] Check logs: `C:\Users\USERNAME\AppData\Roaming\Claude\logs\`
- [ ] Look for connection errors
- [ ] Verify tools appear in Claude Desktop
- [ ] Test tool execution in Claude chat

---

## Common Error Patterns & Solutions

### **Error: "Request timed out"**

**Causes:**
1. Protocol version mismatch
2. Server not responding to initialize
3. Server exits after first request (not persistent)
4. Buffered output (missing `-u` flag)

**Debug:**
```bash
# Test initialize directly
echo '{"jsonrpc":"2.0","method":"initialize",...}' | docker exec -i CONTAINER python -u /app/server.py
# Should respond in < 1 second
```

### **Error: "No such container"**

**Cause:** Wrong container name in config

**Solution:**
```bash
docker compose ps  # Get actual name
# Update config with exact name
```

### **Error: "Tool 'X' not found"**

**Causes:**
1. Server not actually connected (just cached from previous session)
2. tools/call not implemented correctly
3. Tool name mismatch

**Debug:** Check logs for actual tools/call request and response

### **Error: "Server disconnected"**

**Causes:**
1. Container stopped/crashed
2. Python exception in server
3. Invalid JSON response

**Debug:**
```bash
docker logs CONTAINER_NAME  # Check for Python errors
docker compose ps            # Verify container running
```

---

## Architecture Evolution

### **Initial (Failed) Architecture:**

```
Claude Desktop
    ↓ (stdio)
curl wrapper script
    ↓ (HTTPS)
nginx reverse proxy (port 8443)
    ↓ (HTTP)
Flask HTTP server (port 8000)
```

**Problems:**
- Curl exits after one request
- Complex, brittle chain
- Protocol translation issues

### **Final (Working) Architecture:**

```
Claude Desktop
    ↓ (stdio via wsl docker exec)
MCP Python SDK Server (in container)
```

**Benefits:**
- ✅ Direct stdio communication
- ✅ Persistent connection
- ✅ MCP protocol compliance
- ✅ Simple, reliable
- ✅ Easy to debug

---

## Time Investment Reality

### **Estimated vs. Actual:**

| Phase | Estimated | Actual | Notes |
|-------|-----------|--------|-------|
| Phase 1 (Prerequisites) | 30 min | 45 min | SSH setup took longer |
| Phase 2 (Environment) | 10-15 min | 25 min | Multiple iterations needed |
| Phase 3 (Integration) | 15 min | 3+ hours | HTTP approach completely wrong |
| **Total** | **55-60 min** | **4+ hours** | Learning MCP protocol properly |

### **Future Setups (with correct approach):**

| Phase | Time | Notes |
|-------|------|-------|
| Phase 1 | 30-45 min | Prerequisites unchanged |
| Phase 2 | 15-20 min | Use MCP SDK from start |
| Phase 3 | 10-15 min | Known working config |
| **Total** | **55-80 min** | Much faster with correct approach |

---

## Key Takeaways

### **Do:**

1. ✅ Use MCP Python SDK from the start
2. ✅ Implement stdio transport (not HTTP)
3. ✅ Test each MCP method individually before integrating
4. ✅ Match protocol version exactly (2025-06-18)
5. ✅ Use full container names (with project prefix)
6. ✅ Use `python -u` for unbuffered output
7. ✅ Verify with `docker compose ps` before config
8. ✅ Test manually with echo/docker exec before Claude Desktop
9. ✅ Check logs in `C:\Users\...\AppData\Roaming\Claude\logs\`
10. ✅ Use `wsl` command from Windows config

### **Don't:**

1. ❌ Build HTTP servers for MCP (use stdio)
2. ❌ Use curl wrappers for stdio communication
3. ❌ Assume container names (always verify)
4. ❌ Use buffered Python output (always use `-u`)
5. ❌ Guess protocol versions (check Claude Desktop logs)
6. ❌ Put config in WSL filesystem (use Windows path)
7. ❌ Skip manual testing before integration
8. ❌ Ignore stderr output (contains valuable errors)

---

## Documentation Updates Required

Based on these lessons, the following documents need updates:

1. **FRESH_WORKSTATION_SETUP.md**
   - Phase 2: Emphasize MCP SDK approach
   - Phase 3: Complete Claude Desktop integration guide
   - Add troubleshooting for all issues we hit

2. **README.md** (in mcp-dev-environment repo)
   - Update architecture diagram
   - Remove references to nginx/HTTP approach
   - Add MCP SDK quick start

3. **New: MCP_SERVER_DEVELOPMENT_GUIDE.md**
   - How to create MCP servers using SDK
   - Testing checklist
   - Integration guide

4. **New: ARCHITECTURE.md**
   - Final architecture documentation
   - Why stdio vs. HTTP
   - Container communication patterns

---

## Next Steps for Future Developers

When setting up a new MCP development environment:

1. **Start:** Follow FRESH_WORKSTATION_SETUP.md (updated version)
2. **Create Server:** Use MCP Python SDK template
3. **Test Locally:** Use echo/docker exec commands
4. **Integrate:** Follow Claude Desktop config checklist
5. **Debug:** Use this lessons learned doc for common issues

---

## Conclusion

The most critical lesson: **MCP servers must use stdio transport with the official SDK.** The HTTP/curl approach cannot work for Claude Desktop integration due to the persistent, bidirectional nature of the MCP protocol.

All other issues (protocol version, container names, config location) were relatively minor and easily fixed once the fundamental architecture was correct.

**Total development time saved for future developers:** 2-3 hours by avoiding the HTTP approach entirely.

---

**Document Version:** 1.0  
**Last Updated:** December 1, 2025  
**Status:** Validated - Working Implementation  
