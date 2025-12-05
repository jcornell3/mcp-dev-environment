# Debug Logging Test Guide

## What Was Updated

Added detailed debug logging to the Universal Cloud Connector to understand why request IDs are not being found when responses arrive:

1. **Line 242 in dist/index.js** (main function):
   ```
   [DEBUG] Added request id {id} to pendingRequests. Map size: {size}
   ```
   This logs when a request ID is added to the pending map.

2. **Line 84 in dist/index.js** (SSE handler):
   ```
   [DEBUG-SSE] Received response for id {id}. pendingRequests has {size} entries. Keys: {key1, key2, ...}
   ```
   This logs what's in the pendingRequests map when a response arrives.

## Testing Steps

### Step 1: Restart Claude Desktop (Again)
1. Completely exit Claude Desktop
2. Wait 5 seconds
3. Relaunch Claude Desktop

### Step 2: Test Math Bridge and Check Logs

Send a simple message: "Calculate 10 + 5"

Then check the logs immediately:
```
/mnt/c/Users/jcorn/AppData/Roaming/Claude/logs/mcp-server-math-bridge.log
```

### Step 3: Look for Debug Messages

Search for lines with `[DEBUG]`:

Expected sequence:
```
[DEBUG] Added request id 0 to pendingRequests. Map size: 1
[DEBUG-SSE] Received response for id 0. pendingRequests has 1 entries. Keys: 0
[DEBUG] Added request id 1 to pendingRequests. Map size: 1
[DEBUG-SSE] Received response for id 1. pendingRequests has 1 entries. Keys: 1
```

### Step 4: Report One of These Three Scenarios

**Scenario A** (Code is working correctly):
```
[DEBUG] Added request id 1 to pendingRequests. Map size: 1
[DEBUG-SSE] Received response for id 1. pendingRequests has 1 entries. Keys: 1
```
→ If this appears, the fix IS working but there's a different problem downstream

**Scenario B** (Request ID is NOT being added):
```
[No [DEBUG] message appearing at all]
[DEBUG-SSE] Received response for id 1. pendingRequests has 0 entries. Keys:
```
→ This means the code to add the request ID isn't executing

**Scenario C** (Request ID is added but cleared before response):
```
[DEBUG] Added request id 1 to pendingRequests. Map size: 1
[DEBUG-SSE] Received response for id 1. pendingRequests has 0 entries. Keys:
```
→ This means something is clearing the map between adding and receiving

### Step 5: Send the Debug Log

Once you've identified which scenario you see, please share:
1. The relevant section of `/mnt/c/Users/jcorn/AppData/Roaming/Claude/logs/mcp-server-math-bridge.log`
2. Which scenario (A, B, or C) matches what you're seeing

This will help pinpoint the exact problem.

## Why This Matters

The debug logs will tell us:
- If the request ID is actually being set in the map
- If the map is empty when the response arrives
- If something is between getting cleared unexpectedly

This is the missing piece of information needed to fix the underlying issue.
