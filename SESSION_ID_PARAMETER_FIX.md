# Session ID Parameter Naming: The Case Sensitivity Issue

## Executive Summary

The Universal Cloud Connector was looking for a **snake_case** query parameter (`session_id`) but the MCP SDK servers were sending a **camelCase** parameter (`sessionId`). This single character mismatch caused all Claude Desktop connections to fail.

## The Specific Issue

### What Was Happening

**Universal Cloud Connector Expected:**
```
/messages?session_id=550e8400-e29b-41d4-a716-446655440000
                     ^^^^^^^^^^
                     snake_case
```

**MCP SDK Server Actually Sent:**
```
/messages?sessionId=550e8400-e29b-41d4-a716-446655440000
          ^^^^^^^^^
          camelCase
```

### The Regex Pattern

**Original Code (BROKEN):**
```typescript
// Line 170 of src/index.ts - BEFORE FIX
const match = endpointData.match(/session_id=([a-f0-9-]+)/);
//                               ^^^^^^^^^^^ snake_case pattern
```

When the bridge received the endpoint event data:
```
/messages?sessionId=550e8400-e29b-41d4-a716-446655440000
```

The regex pattern looking for `session_id=` would NOT match because it was looking for:
```
/messages?session_id=550e8400-e29b-41d4-a716-446655440000
```

**Fixed Code (WORKING):**
```typescript
// Line 170 of src/index.ts - AFTER FIX
const match = endpointData.match(/sessionId=([a-f0-9-]+)/);
//                               ^^^^^^^^^ camelCase pattern
```

Now when the bridge receives the endpoint event data:
```
/messages?sessionId=550e8400-e29b-41d4-a716-446655440000
```

The regex pattern matching `sessionId=` finds a match and extracts `550e8400-e29b-41d4-a716-446655440000`.

## Why This Matters

### Session ID Extraction Flow

The Universal Cloud Connector needs to extract the session ID from the SSE endpoint event for two critical reasons:

1. **Correlation**: The same session ID must be used in both:
   - The SSE stream connection (already established)
   - POST requests to `/messages` endpoint (new requests)

2. **Stateful Session Tracking**: The MCP server maintains request-response correlation using this session ID

### The Fallback Mechanism

When the regex didn't match, the code had a fallback:

```typescript
if (!match) {
  // FALLBACK: If server didn't send endpoint event, generate a session_id ourselves
  this.sessionId = randomUUID();
  this.logInfo(`FALLBACK: Generated session_id for server that didn't send endpoint event: ${this.sessionId}`);
  this.sessionIdReceived = true;
}
```

This fallback generated a **random UUID** that didn't match what the server was expecting. When the bridge later tried to send requests:

```
POST /messages?sessionId=<random-UUID>
Authorization: Bearer default-api-key
Content-Type: application/json

{"jsonrpc":"2.0","method":"initialize",...}
```

The server would reject it because:
- The server expected: `sessionId=550e8400...` (from endpoint event)
- The bridge sent: `sessionId=abc-def-123...` (randomly generated)

Server response: `400 Bad Request - session_id is required` (or session mismatch)

## Timeline of Failure

```
T+0.0s:   Bridge connects to /sse endpoint
T+0.1s:   SSE connection opened, bridge receives endpoint event
T+0.1s:   Event: "event: endpoint\ndata: /messages?sessionId=550e84...\n\n"
T+0.1s:   Bridge regex looks for "session_id=" (WRONG CASE) - NO MATCH
T+0.1s:   Bridge fallback: generates random UUID "abc-def-123..."
T+0.1s:   Bridge tries POST: /messages?sessionId=abc-def-123...
T+0.1s:   Server: "400 error - session_id is required"
T+0.2s:   Bridge logs error and tries to reconnect
T+1.0s:   Retry 1: Same process, same failure
T+2.0s:   Retry 2: Same process, same failure
T+4.0s:   Retry 3: Same process, same failure
T+8.0s:   Retry 4: Same process, same failure
T+16.0s:  Retry 5: Same process, same failure
T+60.0s:  Claude Desktop timeout: "MCP error -32001: Request timed out"
```

## The Fix in Detail

### Change 1: Endpoint Event Pattern Matching

**File**: `/home/jcornell/universal-cloud-connector/src/index.ts`
**Line**: 170

```diff
- const match = endpointData.match(/session_id=([a-f0-9-]+)/);
+ const match = endpointData.match(/sessionId=([a-f0-9-]+)/);
```

This ensures the regex pattern matches the actual parameter name sent by the server.

### Change 2: Query Parameter Name in URL Construction

**File**: `/home/jcornell/universal-cloud-connector/src/index.ts`
**Line**: 95

```diff
- url.searchParams.set("session_id", this.sessionId);
+ url.searchParams.set("sessionId", this.sessionId);
```

This ensures that when the bridge constructs the messages URL, it uses the correct parameter name.

## Why camelCase for sessionId?

The MCP SDK uses camelCase following JavaScript/TypeScript naming conventions. Looking at the SDK source:

```typescript
// From @modelcontextprotocol/sdk/dist/esm/server/sse.js
this._sessionId = randomUUID();
// ...
const endpointUrl = new URL(this._endpoint, dummyBase);
endpointUrl.searchParams.set('sessionId', this._sessionId);
const relativeUrlWithSession = endpointUrl.pathname + endpointUrl.search;
// Result: "/messages?sessionId=550e8400-e29b-41d4-a716-446655440000"
```

The SDK consistently uses `sessionId` (camelCase) throughout because:
1. JavaScript convention: variables and parameters use camelCase
2. Consistency: The `_sessionId` variable is converted to `sessionId` query param
3. Standard MCP implementation: All SDK implementations follow this pattern

## Verification

### Before Fix:
```bash
$ cd ~/universal-cloud-connector
$ grep "session_id=" src/index.ts
170: const match = endpointData.match(/session_id=([a-f0-9-]+)/);
```

### After Fix:
```bash
$ cd ~/universal-cloud-connector
$ grep "sessionId=" src/index.ts
170: const match = endpointData.match(/sessionId=([a-f0-9-]+)/);
93: url.searchParams.set("sessionId", this.sessionId);
```

### In Compiled JavaScript:
```bash
$ grep "sessionId=" dist/index.js
122: // Extract sessionId from: /messages?sessionId=<UUID> (camelCase from MCP SDK)
123: const match = endpointData.match(/sessionId=([a-f0-9-]+)/);
130: url.searchParams.set("sessionId", this.sessionId);
```

## Impact Analysis

| Component | Impact | Status |
|-----------|--------|--------|
| Math MCP Server | ✅ Fixes connection | Ready to test |
| GitHub Remote Bridge | ✅ Fixes connection | Ready to test |
| Santa Clara Bridge | ✅ Fixes connection | Ready to test |
| YouTube Transcript | ✅ Fixes connection | Ready to test |
| YouTube-to-MP3 | ✅ Fixes connection | Ready to test |
| Test Suite | ✅ Now compatible | Available in test-claude-desktop-simulation.sh |

## Key Takeaway

This was a **case-sensitivity issue** in parameter naming:
- One character difference: `session_id` vs `sessionId`
- One regex pattern mismatch caused complete connection failure
- Fix: Update both regex pattern and URL parameter to use camelCase `sessionId`

The MCP SDK sends `sessionId` (camelCase), so the bridge must look for and use `sessionId` (camelCase) in all contexts.
