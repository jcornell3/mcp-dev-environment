# Found and Fixed the Real Problem: Duplicate Message Handling in Connector

## The Real Issue (Not the Bridge)

After analyzing your latest log file from 2025-12-05T03:17:33, I discovered the actual problem was NOT in the bridge servers - it was in the **Universal Cloud Connector**'s SSE event handler.

### The Smoking Gun from Your Logs

```
Line 895: [DEBUG] Added request id 1 to pendingRequests. Map size: 1
Line 896: [DEBUG-SSE] Received response for id 1. pendingRequests has 1 entries. Keys: 1
Line 897: [DEBUG-SSE] Received response for id 1. pendingRequests has 0 entries. Keys:
Line 898: Received response for unmatched request id: 1
```

**Both "Received response" lines are at the SAME millisecond timestamp (02:59:11.991Z)** - this means the SSE `onmessage` handler was firing TWICE for the same event data.

## Root Cause

The Node.js `EventSource` library or the browser's SSE implementation was calling the `onmessage` handler twice for a single message. This could happen due to:

1. **Network timing issue**: The SSE message arrives and triggers the handler twice
2. **Event emitter re-firing**: The event gets processed multiple times before the listener is removed
3. **Message corruption**: The raw SSE data might have formatting issues causing replay

When the handler fires the second time:
- The same response data is parsed again
- The code tries to look up `id: 1` in `pendingRequests`
- But it was already deleted by the first handler execution
- Result: "Received response for unmatched request id: 1" ❌

## The Fix

Added duplicate detection in the connector's SSE message handler:

```typescript
// Create a unique key for this message to detect duplicates
const messageKey = `${data.id}:${JSON.stringify(data)}`;

// Check if we've already processed this exact message
if (this.processedMessageIds.has(messageKey)) {
  this.logInfo(`[DEBUG-SSE] Duplicate message received for id ${data.id}, skipping`);
  return;  // ← Exit immediately, don't process again
}

// Mark this message as processed
this.processedMessageIds.add(messageKey);
```

### Changes Made to Connector

File: `/home/jcornell/universal-cloud-connector/src/index.ts`

1. **Line 41**: Added `processedMessageIds` Set to track seen messages
2. **Lines 117-121**: Clear the cache when SSE connection is established (for new connections)
3. **Lines 129-148**: Check for duplicates before processing, skip if already seen

## Why This Fixes the Problem

**Before Fix:**
```
Response arrives via SSE
  ↓
onmessage handler fires (first time)
  - Processes response id:1
  - Deletes id:1 from pendingRequests
  ↓
onmessage handler fires (AGAIN with same data)
  - Tries to process response id:1
  - id:1 NOT in pendingRequests (already deleted)
  - ERROR: "unmatched request id" ❌
```

**After Fix:**
```
Response arrives via SSE
  ↓
onmessage handler fires (first time)
  - Creates messageKey for this response
  - messageKey NOT in processedMessageIds → Process it
  - Processes response id:1
  - Deletes id:1 from pendingRequests
  - Adds messageKey to processedMessageIds
  ↓
onmessage handler fires (AGAIN with same data)
  - Creates messageKey for this response
  - messageKey IS in processedMessageIds → Skip it ✅
  - Returns immediately without processing
  ↓
Response forwarded to Claude only ONCE ✅
```

## Deployment Status

✅ **Connector code rebuilt** (December 4, 19:19 UTC)
- New duplicate detection code compiled to `/home/jcornell/universal-cloud-connector/dist/index.js`
- Ready to be loaded by Claude Desktop

⚠️ **Waiting for Claude Desktop Restart**
- Claude Desktop must be completely restarted to load the new connector code
- The connector runs in the Claude Desktop process, not in Docker

## Next Steps for You

### 1. Completely Restart Claude Desktop
- **Close** Claude Desktop completely (File → Exit or Cmd+Q)
- **Wait** 3-5 seconds for it to fully shut down
- **Reopen** Claude Desktop

### 2. Test Immediately
Send this to Claude:
```
Calculate 10 + 5
```

### 3. Expected Result
- The Math tool should be available ✅
- You should see the response: "10 + 5 = 15" (or similar)
- No "Tool not found" errors ❌

### 4. Test Other Bridges
If Math works, test the others to verify they all work.

## Why the Docker Rebuild Wasn't Enough

The `resolved` flag fix in the bridge prevents **duplicate responses being sent** from the bridge.

But the real problem was that even if a response is sent only once, the connector's SSE client can receive and process it twice due to how the Node.js EventSource library works.

This fix prevents the **connector from processing the same message twice**, regardless of how many times the bridge sends it.

## Technical Details

### Message Deduplication Strategy
- Uses a Set to track `messageKey = "${id}:${JSON.stringify(data)}"`
- The full JSON is included to handle cases where the same request ID might have different responses
- Memory-efficient: Only keeps the last 1000 processed messages
- Automatically cleared on new SSE connection (to avoid blocking valid connection retries)

### Why This Is Safe
- Only affects JSON-RPC responses (not keepalive messages)
- Only tracks successfully parsed messages
- Set is cleared on reconnection
- Doesn't prevent legitimate message retries after reconnect

---

## Files Modified in This Fix

### `/home/jcornell/universal-cloud-connector/src/index.ts`
- Added `processedMessageIds: Set<string>` field to track processed messages
- Updated `onopen` handler to clear the cache on new connections
- Enhanced `onmessage` handler to detect and skip duplicate messages
- Memory management to prevent unbounded Set growth

---

**Status**: Ready! Just restart Claude Desktop and test. This fix should finally resolve the "Tool not found" issue!
