# MCP Development Environment - Troubleshooting Guide

**Last Updated**: December 6, 2025

This document covers all known issues, their root causes, and solutions for the MCP Development Environment and Universal Cloud Connector Bridge.

---

## Table of Contents

1. [Universal Cloud Connector Bridge Issues](#universal-cloud-connector-bridge-issues)
2. [GitHub MCP Server Wrapper Issues](#github-mcp-server-wrapper-issues)
3. [Claude Desktop Integration Issues](#claude-desktop-integration-issues)
4. [Historical Issues (Resolved)](#historical-issues-resolved)

---

## Universal Cloud Connector Bridge Issues

### Issue 1: SSE Endpoint Event Race Condition

**Status**: ✅ FIXED (December 6, 2025)

#### Symptoms
- Bridge connects to SSE endpoint but times out during initialization
- Error: `POST request failed with status 400 - session_id is required`
- Infinite reconnect loops in Claude Desktop logs
- Bridge never receives or processes the `endpoint` event

#### Root Cause
The initialize request from Claude Desktop arrives **before** the bridge receives the SSE endpoint event containing the session_id. The sequence was:

1. Claude Desktop sends initialize request to bridge (via stdin)
2. Bridge accepts request and queues it
3. Bridge connects to SSE endpoint
4. Bridge calls `waitForSessionId()` to wait for the endpoint event
5. **OLD CODE**: Timeout after 1 second (100 attempts × 10ms)
6. Endpoint event typically arrives within 10-60ms, but occasionally takes longer
7. If timeout occurs, bridge tries to POST without session_id → 400 error

#### Evidence
From Claude Desktop logs (`mcp-server-math-bridge.log`):
```
05:17:57.966Z Message from client: {"method":"initialize"...}
05:17:57.612Z INFO: SSE connection established
05:17:57.615Z INFO: [ENDPOINT-EVENT] Received: /messages?session_id=...
05:17:57.616Z INFO: [CRITICAL] Session ID extracted from endpoint: ...
05:17:57.685Z INFO: [SSE-MESSAGE] Received response for id 0
```

**Timeline**: Only 69ms from connection to first response. The 1-second timeout should have been sufficient, but in production there were edge cases where it wasn't.

#### Solution
Extended `waitForSessionId()` timeout from 1 second to 10 seconds in `src/index.ts`:

```typescript
private async waitForSessionId(): Promise<void> {
  let attempts = 0;
  const maxAttempts = 1000; // 10 seconds max wait (1000 × 10ms)

  while (!this.sessionIdReceived && attempts < maxAttempts) {
    await new Promise(resolve => setTimeout(resolve, 10));
    attempts++;

    // Log progress every second
    if (attempts % 100 === 0) {
      this.logInfo(`Still waiting for endpoint event... (${attempts / 100} seconds)`);
    }
  }

  if (!this.sessionIdReceived) {
    this.logError(`Timeout after ${maxAttempts * 10}ms waiting for session_id`);
    throw new Error("Failed to receive endpoint event with session_id");
  }

  this.logInfo(`Session ID ready after ${attempts * 10}ms`);
}
```

#### Key Changes
1. Increased timeout from 1s to 10s (100x safety margin)
2. Added progress logging every second
3. Removed fallback UUID generation (was masking the problem)
4. Throw error instead of silently continuing with invalid session_id
5. Added detailed diagnostic logging

#### Files Modified
- `/home/jcornell/universal-cloud-connector/src/index.ts` (lines 52-75)
- Recompiled to `/home/jcornell/universal-cloud-connector/dist/index.js`

#### Testing
All tests pass with the fix:
- ✅ Standalone EventSource test
- ✅ Claude Desktop protocol flow simulation
- ✅ Direct command test
- ✅ All bridge servers (math, youtube, santa-clara, github) working

---

## GitHub MCP Server Wrapper Issues

### Issue 2: GitHub Wrapper Shared Process Architecture

**Status**: ✅ FIXED (December 6, 2025)

#### Symptoms
- GitHub bridge connects but times out during initialization (60-second timeout)
- Other bridges (math, youtube, santa-clara) work fine
- Initialize request sent but no response received
- Server process exits unexpectedly

#### Root Cause
The GitHub MCP wrapper was using a **fundamentally broken architecture**:

**Old Design (Broken)**:
- ONE shared GitHub MCP server process for ALL clients
- Responses broadcast to all connected SSE sessions
- Server stdin/stdout shared across multiple clients

**Why This Failed**:
MCP over stdio is **stateful and one-to-one**:
- Each MCP session maintains conversation state
- stdin/stdout are single-channel communication
- The server process owns the stdio streams
- Multiple clients cannot share the same stdio streams

**Evidence**:
```
[WRAPPER] New SSE connection established
[WRAPPER] Sent endpoint event
[WRAPPER] Starting GitHub MCP server in stdio mode...  // ONE server for all
[WRAPPER] Broadcasting to all sessions...              // Wrong!
```

#### Solution
Complete rewrite of GitHub wrapper to use **per-session process architecture**:

```javascript
// Each session gets its own dedicated GitHub MCP server process
const serverProcess = spawn('github-mcp-server', ['stdio'], {
  stdio: ['pipe', 'pipe', 'pipe'],
  env: {
    ...process.env,
    GITHUB_PERSONAL_ACCESS_TOKEN: GITHUB_TOKEN,
    GITHUB_TOOLSETS: GITHUB_TOOLSETS
  }
});

const session = {
  id: sessionId,
  serverProcess: serverProcess,  // Dedicated process
  buffer: ''
};

// Send responses ONLY to this session
serverProcess.stdout.on('data', (data) => {
  if (session.listening && session.response) {
    session.response.write(`data: ${JSON.stringify(message)}\n\n`);
  }
});

// Kill server when client disconnects
req.on('close', () => {
  if (serverProcess && !serverProcess.killed) {
    serverProcess.kill();
  }
});
```

#### Key Changes
1. Spawn one GitHub server process per SSE session
2. Each session has dedicated stdin/stdout streams
3. Server process lifecycle tied to client connection
4. Proper cleanup on disconnect
5. Added line buffering for JSON parsing

#### Files Modified
- `/home/jcornell/mcp-dev-environment/servers/shared/github-mcp-http-wrapper/server.js` (complete rewrite)

#### Architecture Now Consistent
This brings the GitHub wrapper in line with Python MCP server wrappers, which already used per-session processes.

#### Testing
```bash
# Test shows successful initialization
[2025-12-06T14:13:59.799Z] INFO: SSE connection established
[2025-12-06T14:13:59.800Z] INFO: [ENDPOINT-EVENT] Received
[2025-12-06T14:13:59.800Z] INFO: Session ID extracted
[2025-12-06T14:13:59.805Z] INFO: Session ID ready after 10ms
[2025-12-06T14:13:59.833Z] INFO: Initialize response received
```

GitHub tools verified working in Claude Desktop:
- ✅ Repository search
- ✅ File content retrieval
- ✅ Issue listing
- ✅ PR operations
- ✅ Code search

---

## Claude Desktop Integration Issues

### Issue 3: Chat Session Isolation

**Status**: 📝 DOCUMENTED (Not a bug - by design)

#### Symptoms
- MCP tools work in one chat but not another
- After restarting Claude Desktop, tools not available in new chats
- Tools appear in "running" status but AI can't access them

#### Root Cause
This is **Claude Desktop's intended behavior**, not a bug:

**How Claude Desktop Works**:
1. MCP servers initialize when Claude Desktop starts
2. Tools are bound to the **active chat session** at initialization time
3. New chat sessions don't automatically inherit tools from other sessions
4. Each chat has its own isolated tool context

#### Evidence
From `mcp-info.json`:
```json
{
  "activeServers": [
    "math-bridge",
    "santa-clara-bridge"
  ],
  "configurations": {
    "math-bridge": {
      "status": "running"
    }
  }
}
```

Servers show "running" but tools only available in specific chat sessions.

#### Solution
**To use MCP tools in a new chat**:
1. Restart Claude Desktop completely (close all windows)
2. Open Claude Desktop fresh
3. Start a NEW chat session
4. Tools will be available in this new session

**Alternatively**:
1. Keep using the chat session where tools are working
2. Don't create new chats if you need the tools

#### Why This Matters
- Tools from old sessions are "orphaned" when you create new chats
- This explains why the same tools work in tests but not in Claude Desktop
- It's not a bridge issue - it's Claude Desktop's session management

---

## Historical Issues (Resolved)

These issues were encountered and fixed during development. They are documented here for reference but should not occur in the current system.

### Session ID Correlation Issues (Fixed: Early December 2025)

**Symptom**: Responses from MCP servers not reaching the correct clients.

**Cause**: Bridge wasn't properly tracking which request belonged to which session.

**Fix**: Implemented `pendingRequests` Map to correlate requests with responses using request IDs.

**Status**: ✅ Resolved in current code

---

### Duplicate Message Issues (Fixed: Early December 2025)

**Symptom**: Same response delivered multiple times to Claude Desktop.

**Cause**: No deduplication of SSE messages.

**Fix**: Added `processedMessageIds` Set to track and skip duplicate messages.

**Status**: ✅ Resolved in current code

---

### PowerShell Bridge Empty Response (Fixed: November 2025)

**Symptom**: PowerShell-based bridge not returning responses.

**Cause**: Incorrect stream handling in PowerShell wrapper.

**Fix**: Migrated to TypeScript/Node.js bridge (universal-cloud-connector).

**Status**: ✅ Resolved - PowerShell bridge deprecated

---

### Caddy Reverse Proxy Issues (Fixed: November 2025)

**Symptom**: SSE connections not working through Caddy reverse proxy.

**Cause**: Caddy buffering SSE responses.

**Fix**: Added `flush_interval -1` to Caddy configuration.

**Status**: ✅ Resolved in Caddyfile

---

## Diagnostic Procedures

### How to Diagnose Bridge Issues

1. **Check Claude Desktop Logs**
   ```
   Help → Export Logs → Extract zip → Open mcp-server-[name]-bridge.log
   ```

2. **Look for Key Indicators**
   - ✅ Good: `[ENDPOINT-EVENT] Received`
   - ✅ Good: `Session ID extracted from endpoint`
   - ✅ Good: `Session ID ready after Xms`
   - ❌ Bad: `POST request failed with status 400`
   - ❌ Bad: `Reconnecting in 1000ms`
   - ❌ Bad: `ERROR: SSE connection error`

3. **Check Server Health**
   ```bash
   curl http://127.0.0.1:3001/health  # Math
   curl http://127.0.0.1:3002/health  # Santa Clara
   curl http://127.0.0.1:3003/health  # YouTube Transcript
   curl http://127.0.0.1:3004/health  # YouTube to MP3
   curl http://127.0.0.1:3005/health  # GitHub
   ```

4. **Test Bridge Directly**
   ```bash
   cd /home/jcornell/universal-cloud-connector
   ./run-all-tests.sh
   ```

5. **Check Docker Containers**
   ```bash
   docker ps | grep mcp
   docker logs mcp-dev-environment-[server]-1
   ```

### Common Solutions

#### Bridge Not Responding
1. Rebuild bridge: `npm run build`
2. Restart Claude Desktop
3. Check if server containers are running
4. Review server logs for errors

#### Tools Not Available in Claude Desktop
1. Restart Claude Desktop completely
2. Create a NEW chat session
3. Wait 5-10 seconds for initialization
4. Try using tools in the new session

#### Server Container Issues
1. Check container status: `docker ps`
2. Restart specific server: `docker-compose restart [server-name]`
3. Check logs: `docker logs [container-name]`
4. Rebuild if needed: `docker-compose build --no-cache [server-name]`

---

## Prevention Best Practices

### For Developers

1. **Always wait for endpoint event** before processing requests
2. **Use per-session processes** for stdio-based MCP servers
3. **Test with Claude Desktop protocol flow**, not just isolated tests
4. **Add comprehensive logging** for debugging
5. **Handle connection lifecycle** properly (cleanup on disconnect)

### For Users

1. **Restart Claude Desktop** after any bridge/server changes
2. **Create new chat sessions** to get fresh tool bindings
3. **Check server health** before reporting issues
4. **Export logs** when troubleshooting
5. **Keep Docker containers running** in the background

---

## Getting Help

If you encounter issues not covered here:

1. **Export Claude Desktop logs** (Help → Export Logs)
2. **Check server logs** (`docker logs [container]`)
3. **Run test suite** (`./run-all-tests.sh`)
4. **Review this document** for similar issues
5. **Create detailed issue report** with logs and steps to reproduce

---

## Document History

- **December 6, 2025**: Initial comprehensive troubleshooting guide
  - Documented SSE endpoint event race condition fix
  - Documented GitHub wrapper architecture fix
  - Documented Claude Desktop session isolation behavior
  - Consolidated historical issues
