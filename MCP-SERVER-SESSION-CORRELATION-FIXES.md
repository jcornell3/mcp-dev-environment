# MCP Server Session Correlation Fixes

## Problem
Claude Desktop couldn't discover tools from the Math, Santa Clara, YouTube Transcript, and YouTube to MP3 MCP servers. The root cause was a session correlation issue in the SSE transport implementation.

## Root Cause Analysis
The MCP (Model Context Protocol) SSE transport requires:
1. A single SSE transport instance to maintain session state
2. The GET /sse endpoint to establish the connection and create a session
3. The POST /messages endpoint to correlate incoming requests to the same session

The code was creating **separate transport instances** for each endpoint, breaking the correlation:
- `/sse` GET endpoint created Transport Instance A
- `/messages` POST endpoint created Transport Instance B
- POST requests couldn't find their session → "session_id is required" error

## Fixes Applied

### Fix 1: Global SSE Transport Instance
Created a module-level global `sse_transport` instance instead of creating new ones per request:

```python
# Global SSE transport instance - shared across /sse and /messages endpoints
# This maintains session state and correlates SSE streams with POST messages
sse_transport = SseServerTransport(endpoint="/messages")
```

### Fix 2: Proper Stream Unpacking
The `connect_sse()` context manager yields a tuple `(read_stream, write_stream)`, not an awaitable:

```python
# Correct: Unpack the tuple
async with sse_transport.connect_sse(...) as (read_stream, write_stream):
    await server.run(read_stream, write_stream, server.create_initialization_options())

# Incorrect (was doing before): Try to await a tuple
async with sse_transport.connect_sse(...) as sse:
    await sse  # TypeError: object tuple can't be used in 'await' expression
```

### Fix 3: Mount /messages Endpoint Directly
The critical pattern is to Mount the SSE transport's `handle_post_message` directly as an ASGI application, NOT as a regular FastAPI route. This preserves the transport's internal session tracking:

```python
# Correct: Mount the transport handler directly
async def messages_endpoint(scope, receive, send):
    """Messages endpoint that delegates to SSE transport"""
    await sse_transport.handle_post_message(scope, receive, send)

app.routes.append(Mount("/messages", app=messages_endpoint))

# Incorrect: Wrapping in a FastAPI route handler breaks session correlation
@app.post("/messages")
async def messages_handler(request: Request):
    # This creates a new context, breaking the SSE session linkage
    return await sse_transport.handle_post_message(...)
```

The SSE endpoint properly unpacks and handles the streams:

```python
@app.get("/sse")
@app.get("/sse/")
async def sse_stream(request: Request):
    # Use global transport instance to maintain session state
    async with sse_transport.connect_sse(...) as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
```

## Files Modified
- servers/math/server.py
- servers/santa-clara/server.py
- servers/youtube-transcript/server.py
- servers/youtube-to-mp3/server.py

## Result
- ✅ SSE transport maintains single session across both endpoints
- ✅ POST /messages requests can now find their session_id
- ✅ MCP protocol handshake completes successfully
- ✅ Tools from all 4 servers should now be discoverable in Claude Desktop

## How It Works Now
1. Claude Desktop connects to bridge at http://127.0.0.1:3001/sse (Math server example)
2. Bridge establishes GET /sse connection
3. Global `sse_transport` creates a new session with unique session_id
4. MCP initialize request is sent
5. All subsequent POST /messages requests use the same transport instance
6. Session_id is found and correlated correctly
7. Tools are listed and can be called

## Testing
- Docker containers rebuilt and restarted
- Math server logs show clean startup with no errors
- Health endpoint responds correctly: `{"status":"healthy","service":"math","api_key_configured":false}`
- No more "session_id is required" errors expected in Claude Desktop logs
