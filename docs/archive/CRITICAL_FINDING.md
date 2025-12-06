# CRITICAL FINDING: The Same Response is Being Received TWICE

## The Discovery

Analysis of the debug logs reveals a smoking gun. Look at these exact log lines from the most recent test:

```
895→[DEBUG] Added request id 1 to pendingRequests. Map size: 1
896→[2025-12-05T02:59:11.991Z] INFO: [DEBUG-SSE] Received response for id 1. pendingRequests has 1 entries. Keys: 1
897→[2025-12-05T02:59:11.991Z] INFO: [DEBUG-SSE] Received response for id 1. pendingRequests has 0 entries. Keys:
898→[2025-12-05T02:59:11.991Z] INFO: Received response for unmatched request id: 1
```

**The SSE handler is processing the response for id:1 TWICE in the same millisecond!**

### Timeline:
1. **Line 895**: Request id:1 is added to pendingRequests ✅
2. **Line 896**: SSE handler receives id:1, map HAS the entry ✅ (deletes it after forwarding)
3. **Line 897**: **Same SSE handler receives id:1 AGAIN**, but now map is EMPTY ❌
4. **Line 898**: Response is dropped as unmatched

## Why This Happens

There are two possibilities:

### Possibility A: Multiple Connector Instances
The bridge may be receiving connections from **MULTIPLE connector instances** running at the same time, and they're both receiving the same broadcast message.

When the bridge sends a response via SSE, it broadcasts to ALL connected clients:
```javascript
for (const [clientId, client] of connectedClients.entries()) {
  client.res.write(data);  // Sends to each client
}
```

If TWO connector instances are connected simultaneously, they both receive the message!

### Possibility B: SSE Client Receiving Message Twice
The EventSource (SSE client in the connector) might be firing the `onmessage` handler twice for a single message from the bridge.

## How to Test This

We added new logging to the bridge to reveal how many clients are connected:

```
[Bridge] Broadcasting to {N} connected clients for message id: {id}
```

### Next Steps for You:

1. **Restart Claude Desktop completely**
2. **Test: "Calculate 10 + 5"**
3. **Check both logs:**
   - `/mnt/c/Users/jcorn/AppData/Roaming/Claude/logs/mcp-server-math-bridge.log`
   - `docker logs mcp-dev-environment-bridge-math-1`

### What to Look For:

**In Claude's log file** (math-bridge.log):
- Look for lines with `[DEBUG] Added request id`
- Count how many `[DEBUG-SSE]` lines appear for each id

**In Docker bridge log**:
- Look for lines with `Broadcasting to X connected clients`
  - If it says `Broadcasting to 2 connected clients`, we found the problem!
  - If it says `Broadcasting to 1 connected client`, then something else is happening

### Expected Output if Multiple Clients:

```
[Bridge] Broadcasting to 2 connected clients for message id: 1
[Bridge] Sent response via SSE to client client-1 (id: 1)
[Bridge] Sent response via SSE to client client-2 (id: 1)
```

Then in the Claude log, you'd see the message received twice.

### Expected Output if Single Client:

```
[Bridge] Broadcasting to 1 connected clients for message id: 1
[Bridge] Sent response via SSE to client client-1 (id: 1)
```

Then in the Claude log, you'd see only ONE `[DEBUG-SSE]` line per id.

## Why This Matters

This is the KEY to fixing the problem:

- **If multiple clients**: We need to prevent multiple connector instances from running simultaneously
- **If single client**: There's an issue with how the EventSource is handling messages

Please run the test and report what the bridge logs show for "Broadcasting to X connected clients"!
