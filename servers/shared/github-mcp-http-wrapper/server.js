#!/usr/bin/env node

/**
 * HTTP/SSE Wrapper for GitHub MCP Server
 * Converts stdio-based MCP server to HTTP/SSE transport for use with Universal Cloud Connector Bridge
 */

const http = require('http');
const { spawn } = require('child_process');
const { randomUUID } = require('crypto');

const PORT = process.env.PORT || 3000;
const SERVER_HOST = '0.0.0.0';
const GITHUB_TOKEN = process.env.GITHUB_PERSONAL_ACCESS_TOKEN || '';
const GITHUB_TOOLSETS = process.env.GITHUB_TOOLSETS || 'repos,issues,pull_requests,actions';

// Session management
const sessions = new Map();
let serverProcess = null;
let serverReadyPromise = null;
let serverReadyResolve = null;

// Initialize ready promise
serverReadyPromise = new Promise((resolve) => {
  serverReadyResolve = resolve;
});

// Start the GitHub MCP server in stdio mode
function startGitHubServer() {
  console.log('[WRAPPER] Starting GitHub MCP server in stdio mode...');

  serverProcess = spawn('github-mcp-server', ['stdio'], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: {
      ...process.env,
      GITHUB_PERSONAL_ACCESS_TOKEN: GITHUB_TOKEN,
      GITHUB_TOOLSETS: GITHUB_TOOLSETS
    }
  });

  let initMessageReceived = false;

  // Handle server stdout (responses from server)
  serverProcess.stdout.on('data', (data) => {
    const lines = data.toString().split('\n').filter(l => l);
    lines.forEach(line => {
      try {
        const message = JSON.parse(line);

        // Log first message to know server is ready
        if (!initMessageReceived && message.jsonrpc) {
          initMessageReceived = true;
          console.log('[WRAPPER] GitHub MCP server ready');
          serverReadyResolve();
        }

        // Broadcast to all listening sessions
        for (const [sessionId, session] of sessions.entries()) {
          if (session.listening && session.response) {
            try {
              session.response.write(`data: ${JSON.stringify(message)}\n\n`);
            } catch (err) {
              console.error(`[WRAPPER] Error sending to session ${sessionId}:`, err.message);
            }
          }
        }
      } catch (err) {
        console.error('[WRAPPER] Error parsing server message:', err.message);
      }
    });
  });

  // Handle server stderr
  serverProcess.stderr.on('data', (data) => {
    const message = data.toString().trim();
    if (message) {
      console.error('[SERVER STDERR]', message);
    }
  });

  serverProcess.on('error', (err) => {
    console.error('[WRAPPER] GitHub MCP Server spawn error:', err);
  });

  serverProcess.on('close', (code) => {
    console.log(`[WRAPPER] GitHub MCP Server exited with code ${code}`);
    // Notify all sessions
    for (const [sessionId, session] of sessions.entries()) {
      if (session.listening && session.response) {
        try {
          session.response.end();
        } catch (err) {
          // Response already ended
        }
      }
    }
  });

  return serverProcess;
}

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
      serverRunning: serverProcess && !serverProcess.killed
    }));
    return;
  }

  // SSE endpoint for session negotiation and streaming responses
  if (req.url === '/sse' && req.method === 'GET') {
    const sessionId = randomUUID().replace(/-/g, '');
    const session = {
      id: sessionId,
      created: Date.now(),
      listening: false,
      response: null
    };
    sessions.set(sessionId, session);

    console.log(`[WRAPPER] New SSE connection: ${sessionId}`);

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

    req.on('close', () => {
      session.listening = false;
      console.log(`[WRAPPER] SSE connection closed: ${sessionId}`);
      // Keep session in map briefly for final messages
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
      res.end(JSON.stringify({ error: 'Invalid session_id' }));
      return;
    }

    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });

    req.on('end', async () => {
      try {
        // Wait for server to be ready
        await serverReadyPromise;

        const message = JSON.parse(body);
        console.log(`[WRAPPER] ${sessionId} -> ${message.method || 'request'}`);

        // Send to GitHub MCP server via stdin
        serverProcess.stdin.write(JSON.stringify(message) + '\n');

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

startGitHubServer();

server.listen(PORT, SERVER_HOST, () => {
  console.log(`[WRAPPER] HTTP server listening on ${SERVER_HOST}:${PORT}`);
  console.log(`[WRAPPER] Health check: http://localhost:${PORT}/health`);
  console.log(`[WRAPPER] SSE endpoint: http://localhost:${PORT}/sse`);
  console.log(`[WRAPPER] Messages endpoint: http://localhost:${PORT}/messages?session_id=<UUID.hex>`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('[WRAPPER] Received SIGTERM, shutting down...');
  if (serverProcess) {
    serverProcess.kill();
  }
  server.close(() => {
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('[WRAPPER] Received SIGINT, shutting down...');
  if (serverProcess) {
    serverProcess.kill();
  }
  server.close(() => {
    process.exit(0);
  });
});
