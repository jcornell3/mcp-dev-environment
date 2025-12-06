#!/usr/bin/env node

/**
 * HTTP/SSE Wrapper for GitHub MCP Server
 * Converts stdio-based MCP server to HTTP/SSE transport for use with Universal Cloud Connector Bridge
 *
 * CRITICAL: Each session gets its own GitHub MCP server process
 * This is required because MCP over stdio is stateful and one-to-one
 */

const http = require('http');
const { spawn } = require('child_process');
const { randomUUID } = require('crypto');

const PORT = process.env.PORT || 3000;
const SERVER_HOST = '0.0.0.0';
const GITHUB_TOKEN = process.env.GITHUB_PERSONAL_ACCESS_TOKEN || '';
const GITHUB_TOOLSETS = process.env.GITHUB_TOOLSETS || 'repos,issues,pull_requests,actions';

// Session management - each session has its own server process
const sessions = new Map();

// Create HTTP server
const server = http.createServer(async (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  // Handle OPTIONS requests
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // Health check endpoint
  if (req.url === '/health' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      activeSessions: sessions.size,
      serverRunning: true
    }));
    return;
  }

  // SSE endpoint for session negotiation and streaming responses
  if (req.url === '/sse' && req.method === 'GET') {
    const sessionId = randomUUID().replace(/-/g, '');

    console.log(`[WRAPPER] New SSE connection: ${sessionId}`);

    // Spawn a dedicated GitHub MCP server for this session
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
      created: Date.now(),
      listening: false,
      response: null,
      serverProcess: serverProcess,
      buffer: ''  // Buffer for incomplete JSON lines
    };
    sessions.set(sessionId, session);

    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*'
    });

    session.response = res;
    session.listening = true;

    // Send endpoint event to establish session
    res.write(`event: endpoint\n`);
    res.write(`data: /messages?session_id=${sessionId}\n\n`);

    console.log(`[WRAPPER] Sent endpoint event for session ${sessionId}`);

    // Handle server stdout (responses from server)
    serverProcess.stdout.on('data', (data) => {
      // Append to buffer
      session.buffer += data.toString();

      // Split by newlines and process complete lines
      const lines = session.buffer.split('\n');
      // Keep the last incomplete line in buffer
      session.buffer = lines.pop() || '';

      lines.forEach(line => {
        if (!line.trim()) return;

        try {
          const message = JSON.parse(line);

          // Send via SSE to this session only
          if (session.listening && session.response) {
            try {
              session.response.write(`data: ${JSON.stringify(message)}\n\n`);
            } catch (err) {
              console.error(`[WRAPPER] Error sending to session ${sessionId}:`, err.message);
            }
          }
        } catch (err) {
          console.error(`[WRAPPER] Error parsing server message for session ${sessionId}:`, err.message);
          console.error(`[WRAPPER] Problematic line: ${line}`);
        }
      });
    });

    // Handle server stderr
    serverProcess.stderr.on('data', (data) => {
      const message = data.toString().trim();
      if (message) {
        console.error(`[SERVER ${sessionId} STDERR]`, message);
      }
    });

    serverProcess.on('error', (err) => {
      console.error(`[WRAPPER] GitHub MCP Server spawn error for session ${sessionId}:`, err);
    });

    serverProcess.on('close', (code) => {
      console.log(`[WRAPPER] GitHub MCP Server for session ${sessionId} exited with code ${code}`);
      if (session.listening && session.response) {
        try {
          session.response.end();
        } catch (err) {
          // Response already ended
        }
      }
      // Clean up session
      setTimeout(() => {
        sessions.delete(sessionId);
      }, 100);
    });

    req.on('close', () => {
      session.listening = false;
      console.log(`[WRAPPER] SSE connection closed: ${sessionId}`);

      // Kill the server process when client disconnects
      if (serverProcess && !serverProcess.killed) {
        serverProcess.kill();
      }

      // Keep session in map briefly for cleanup
      setTimeout(() => {
        sessions.delete(sessionId);
      }, 1000);
    });

    return;
  }

  // Messages endpoint for MCP requests
  if (req.url.startsWith('/messages') && req.method === 'POST') {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const sessionId = url.searchParams.get('session_id');

    if (!sessionId || !sessions.has(sessionId)) {
      console.error(`[WRAPPER] Invalid session_id: ${sessionId}`);
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'session_id is required' }));
      return;
    }

    const session = sessions.get(sessionId);

    if (!session.serverProcess || session.serverProcess.killed) {
      console.error(`[WRAPPER] Server process dead for session ${sessionId}`);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Server process not running' }));
      return;
    }

    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });

    req.on('end', async () => {
      try {
        const message = JSON.parse(body);
        console.log(`[WRAPPER] Session ${sessionId} -> ${message.method || 'request'} (id: ${message.id})`);

        // Send to this session's GitHub MCP server via stdin
        session.serverProcess.stdin.write(JSON.stringify(message) + '\n');

        // Respond with 202 Accepted
        // The actual response will come via SSE
        res.writeHead(202, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'accepted' }));
      } catch (err) {
        console.error(`[WRAPPER] Error processing message:`, err.message);
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
      }
    });

    return;
  }

  // Root endpoint
  if (req.url === '/' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(`
<!DOCTYPE html>
<html>
<head><title>GitHub MCP HTTP Wrapper</title></head>
<body>
<h1>GitHub MCP HTTP Wrapper</h1>
<p>SSE endpoint: <code>GET /sse</code></p>
<p>Messages endpoint: <code>POST /messages?session_id=...</code></p>
<p>Health check: <code>GET /health</code></p>
<p>Active sessions: ${sessions.size}</p>
<p><strong>Note:</strong> Each session spawns its own GitHub MCP server process</p>
</body>
</html>
    `);
    return;
  }

  // 404
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
});

// Start everything
console.log('[WRAPPER] GitHub MCP HTTP Wrapper starting...');
console.log(`[WRAPPER] GitHub Token: ${GITHUB_TOKEN ? 'set' : 'NOT SET'}`);
console.log(`[WRAPPER] GitHub Toolsets: ${GITHUB_TOOLSETS}`);
console.log(`[WRAPPER] Mode: One server process per session`);

server.listen(PORT, SERVER_HOST, () => {
  console.log(`[WRAPPER] HTTP server listening on ${SERVER_HOST}:${PORT}`);
  console.log(`[WRAPPER] Health check: http://localhost:${PORT}/health`);
  console.log(`[WRAPPER] SSE endpoint: http://localhost:${PORT}/sse`);
  console.log(`[WRAPPER] Messages endpoint: http://localhost:${PORT}/messages?session_id=<UUID.hex>`);
});

// Graceful shutdown
function shutdown() {
  console.log('[WRAPPER] Shutting down...');

  // Kill all session server processes
  for (const [sessionId, session] of sessions.entries()) {
    if (session.serverProcess && !session.serverProcess.killed) {
      console.log(`[WRAPPER] Killing server process for session ${sessionId}`);
      session.serverProcess.kill();
    }
  }

  server.close(() => {
    console.log('[WRAPPER] HTTP server closed');
    process.exit(0);
  });
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
