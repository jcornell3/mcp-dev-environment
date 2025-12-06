# MCP Development Environment - Issues and Fixes (Consolidated)

**Last Updated**: December 6, 2025
**Status**: Production Ready ✅

This document consolidates all issues encountered during MCP development and their resolutions. This supersedes all individual fix documents in the root directory.

---

## Current Production Issues (December 2025)

### 1. Universal Cloud Connector Bridge - SSE Endpoint Race Condition

**Fixed**: December 6, 2025
**Severity**: Critical
**Affected Components**: All bridge servers

#### Problem
Initialize requests from Claude Desktop arrived before the bridge received the SSE endpoint event containing the session_id, causing:
- HTTP 400 errors: "session_id is required"
- Infinite reconnect loops
- Bridge timeouts

#### Root Cause Analysis
```
Timeline:
t=0ms    : Claude Desktop sends initialize to bridge (stdin)
t=3ms    : Bridge queues request, connects to SSE
t=58ms   : SSE connection established
t=59ms   : Endpoint event received with session_id
t=60ms   : waitForSessionId() checks... session_id available!
t=68ms   : Request sent with session_id
t=103ms  : Response received

OLD CODE: waitForSessionId() only waited 1 second (1000ms)
PROBLEM: Occasionally the endpoint event took > 1 second
RESULT: Bridge sent POST without session_id → 400 error
```

#### Solution
Extended `waitForSessionId()` timeout from 1s to 10s with progress logging:

**File**: `/home/jcornell/universal-cloud-connector/src/index.ts` (lines 52-75)

```typescript
private async waitForSessionId(): Promise<void> {
  let attempts = 0;
  const maxAttempts = 1000; // 10 seconds (was 100 = 1 second)

  while (!this.sessionIdReceived && attempts < maxAttempts) {
    await new Promise(resolve => setTimeout(resolve, 10));
    attempts++;

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

#### Verification
All servers tested and working:
- ✅ math-bridge (calculate, factorial)
- ✅ santa-clara-bridge (property lookup)
- ✅ youtube-transcript-bridge (transcripts, languages)
- ✅ youtube-to-mp3-bridge (video conversion)
- ✅ github-remote-bridge (repository operations)

---

### 2. GitHub MCP Wrapper - Shared Process Architecture

**Fixed**: December 6, 2025
**Severity**: Critical
**Affected Components**: GitHub bridge only

#### Problem
GitHub bridge timed out during initialization (60s timeout) while other bridges worked fine. No responses received from GitHub MCP server.

#### Root Cause Analysis
The GitHub wrapper used a fundamentally flawed architecture:

**Broken Design**:
- ONE shared GitHub MCP server process for ALL clients
- Attempted to broadcast stdio responses to multiple SSE sessions
- Server stdin/stdout shared across clients

**Why It Failed**:
- MCP over stdio is **stateful** and **one-to-one**
- Each session needs independent conversation state
- stdio streams cannot be shared between multiple clients
- The Go-based GitHub server expected single-client communication

#### Solution
Complete architectural rewrite to per-session process model:

**File**: `/home/jcornell/mcp-dev-environment/servers/shared/github-mcp-http-wrapper/server.js`

**Key Changes**:
1. Spawn one GitHub server process per SSE connection
2. Each session gets dedicated stdin/stdout streams
3. Server process lifecycle tied to client connection
4. Proper cleanup when client disconnects
5. Added line buffering for JSON parsing

**Before** (Broken):
```javascript
// Global shared server
let serverProcess = spawn('github-mcp-server', ...);

// Broadcast to ALL sessions
serverProcess.stdout.on('data', (data) => {
  for (const [id, session] of sessions) {
    session.response.write(`data: ${data}\n\n`);
  }
});
```

**After** (Fixed):
```javascript
// Per-session server
const session = {
  serverProcess: spawn('github-mcp-server', ...),
  response: res
};

// Send ONLY to this session
serverProcess.stdout.on('data', (data) => {
  if (session.listening) {
    session.response.write(`data: ${data}\n\n`);
  }
});

// Cleanup on disconnect
req.on('close', () => {
  serverProcess.kill();
});
```

#### Verification
GitHub tools tested and working:
- ✅ Repository search
- ✅ File content retrieval
- ✅ Issue listing
- ✅ Pull request operations
- ✅ Code search

---

## Historical Issues (Resolved During Development)

### 3. Session ID Correlation

**Fixed**: Early December 2025
**Severity**: High

#### Problem
Responses from MCP servers reaching wrong clients or being lost.

#### Solution
Implemented `pendingRequests` Map in bridge to correlate requests with responses using request IDs.

**Status**: ✅ Resolved in current code

---

### 4. Duplicate Message Delivery

**Fixed**: Early December 2025
**Severity**: Medium

#### Problem
Same response delivered multiple times to Claude Desktop causing confusion.

#### Solution
Added `processedMessageIds` Set to deduplicate messages based on content hash.

**Status**: ✅ Resolved in current code

---

### 5. PowerShell Bridge Empty Responses

**Fixed**: November 2025
**Severity**: Critical

#### Problem
Original PowerShell-based bridge not returning responses to Claude Desktop.

#### Solution
Complete migration to TypeScript/Node.js based Universal Cloud Connector Bridge.

**Status**: ✅ Resolved - PowerShell bridge deprecated

---

### 6. Caddy SSE Buffering

**Fixed**: November 2025
**Severity**: High

#### Problem
SSE connections not streaming through Caddy reverse proxy.

#### Solution
Added `flush_interval -1` to Caddyfile for SSE endpoints.

**Status**: ✅ Resolved in production Caddyfile

---

### 7. JSON-RPC Protocol Compliance

**Fixed**: November 2025
**Severity**: Medium

#### Problem
Various protocol compliance issues with JSON-RPC 2.0 specification.

#### Solution
Strict validation and compliance implementation in bridge code.

**Status**: ✅ Resolved - full JSON-RPC 2.0 compliance

---

## Known Limitations (Not Bugs)

### Claude Desktop Chat Session Isolation

**Status**: By Design ℹ️

#### Behavior
MCP tools are bound to specific chat sessions. Creating a new chat in Claude Desktop doesn't automatically provide access to MCP tools.

#### Why This Happens
Claude Desktop binds MCP servers to the active chat session during initialization. New chats don't inherit tool registrations.

#### Workaround
To use MCP tools in a new chat:
1. Close Claude Desktop completely
2. Reopen Claude Desktop
3. Create a new chat
4. Tools will be available in the new session

**This is not a bug** - it's Claude Desktop's session management design.

---

## Prevention Guidelines

### For Bridge Development

1. **Always handle async properly**: Wait for all required events before processing
2. **Use adequate timeouts**: Network operations need generous timeouts
3. **Log extensively**: Diagnostic logging is critical for troubleshooting
4. **Test with real Claude Desktop**: Isolated tests don't catch all issues
5. **Handle lifecycle correctly**: Clean up resources on disconnect

### For MCP Server Wrappers

1. **One process per session**: Never share stdio streams between clients
2. **Proper buffering**: Handle partial JSON messages correctly
3. **Lifecycle management**: Kill server processes when clients disconnect
4. **Error handling**: Log all errors with context
5. **Health checks**: Implement /health endpoints for monitoring

### For Deployment

1. **Restart Claude Desktop** after any changes
2. **Use new chat sessions** to get fresh tool bindings
3. **Monitor Docker logs** for server issues
4. **Run test suite** before deploying
5. **Keep backups** of working configurations

---

## Testing Procedures

### Automated Tests

Run the comprehensive test suite:
```bash
cd /home/jcornell/universal-cloud-connector
./run-all-tests.sh
```

Expected output:
```
✅ Test 1 PASSED: EventSource library works correctly
✅ Test 2 PASSED: Bridge handles Claude Desktop protocol flow correctly

ALL TESTS PASSED ✅
```

### Manual Testing

1. **Test with Claude Desktop**:
   - Restart Claude Desktop
   - Create new chat session
   - Try each tool category (math, youtube, github, etc.)

2. **Verify Server Health**:
   ```bash
   for port in 3001 3002 3003 3004 3005; do
     echo "Port $port:"
     curl -s http://127.0.0.1:$port/health
   done
   ```

3. **Check Bridge Logs**:
   - Export logs from Claude Desktop
   - Look for endpoint events and session IDs
   - Verify no 400 errors or reconnects

---

## Rollback Procedures

If issues occur after updates:

### Bridge Rollback

1. **Git checkout previous version**:
   ```bash
   cd /home/jcornell/universal-cloud-connector
   git log --oneline
   git checkout <previous-commit>
   npm run build
   ```

2. **Restart Claude Desktop**

### Server Rollback

1. **Use previous Docker image**:
   ```bash
   docker-compose down
   git checkout <previous-commit>
   docker-compose build --no-cache
   docker-compose up -d
   ```

2. **Restart Claude Desktop**

---

## Related Documentation

- **Troubleshooting Guide**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **Architecture**: [ARCHITECTURE.md](../../universal-cloud-connector/docs/ARCHITECTURE.md)
- **Lessons Learned**: [LESSONS_LEARNED_CONSOLIDATED.md](./LESSONS_LEARNED_CONSOLIDATED.md)
- **Setup Guide**: [SETUP_GUIDE.md](./SETUP_GUIDE.md)

---

## Document Supersedes

This document consolidates and supersedes the following:

**In mcp-dev-environment root**:
- BRIDGE_FIX_SUMMARY.md
- CADDY_ISSUE_FIXED.md
- CLAUDE_DESKTOP_FIX_REPORT.md
- COMPLETE_FIX_SUMMARY.md
- CRITICAL_FINDING.md
- DEBUG_LOGGING_TEST.md
- DOCKER_REBUILD_COMPLETE.md
- DUPLICATE_MESSAGE_FIX.md
- FINAL_DIAGNOSIS_AND_FIX.md
- FINAL_FIXES_SUMMARY.md
- FIXES_APPLIED.md
- MCP-SERVER-SESSION-CORRELATION-FIXES.md
- ROOT_CAUSE_ANALYSIS.md
- ROOT_CAUSE_ANALYSIS_FINAL.md
- ROOT_CAUSE_FOUND_AND_FIXED.md
- SESSION_ID_PARAMETER_FIX.md
- TEST-RESULTS-MCP-PROTOCOL-COMPLIANCE.md

**In universal-cloud-connector root**:
- CURRENT_STATUS.md
- DIAGNOSIS.md
- FIX_VERIFIED.md
- GITHUB_BRIDGE_FIXED.md
- CLAUDE_DESKTOP_TOOLS_ISSUE.md

**These files can now be archived or removed as their content is consolidated here.**

---

## Change Log

### December 6, 2025
- Initial consolidated document created
- Documented SSE endpoint race condition fix
- Documented GitHub wrapper architecture fix
- Listed all historical issues
- Added testing and rollback procedures
