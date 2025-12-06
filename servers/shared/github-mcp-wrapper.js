#!/usr/bin/env node

/**
 * Simple SSE wrapper for GitHub MCP Server stdio mode
 * Converts stdio-based MCP server to HTTP/SSE transport
 */

const http = require('http');
const { spawn } = require('child_process');
const { randomUUID } = require('crypto');

const PORT = process.env.PORT || 3000;
const SERVER_HOST = '0.0.0.0';

// Session management
const sessions = new Map();
let serverProcess = null;

// Start the GitHub MCP server in stdio mode
function startGitHubServer() {
  serverProcess = spawn('github-mcp-server', ['stdio'], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: {
      ...process.env,
      GITHUB_PERSONAL_ACCESS_TOKEN: process.env.GITHUB_PERSONAL_ACCESS_TOKEN
    }
  });

  serverProcess.on('error', (err) => {
    console.error('GitHub MCP Server error:', err);
  });

  serverProcess.on('close', (code) => {
    console.log(`GitHub MCP Server exited with code ${code}`);
  });

  return serverProcess;
}

// Create HTTP server
const server = http.createServer((req, res) => {
  // Enable CORS
  res.setHeader('Access-Control-Allow-*', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // SSE endpoint for session negotiation
  if (req.url === '/sse' && req.method === 'GET') {
    const sessionId = randomUUID().replace(/-/g, '');
    const session = {
      id: sessionId,
      created: Date.now(),
      sendQueue: [],
      listening: false
    };
    sessions.set(sessionId, session);

    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*'
    });

    // Send endpoint event to establish session
    res.write(`event: endpoint\n`);
    res.write(`data: /messages?session_id=${sessionId}\n\n`);

    session.listening = true;

    req.on('close', () => {
      session.listening = false;
      console.log(`SSE connection closed for session ${sessionId}`);
    });

    return;
  }

  // Messages endpoint for MCP communication
  if (req.url.startsWith('/messages') && req.method === 'POST') {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const sessionId = url.searchParams.get('session_id');

    if (!sessionId || !sessions.has(sessionId)) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid session_id' }));
      return;
    }

    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });

    req.on('end', () => {
      try {
        const message = JSON.parse(body);
        console.log(`[${sessionId}] Received message:`, message);

        // Send to GitHub MCP server
        serverProcess.stdin.write(JSON.stringify(message) + '\n');

        // For now, respond with 202 Accepted
        // The server will send responses via SSE
        res.writeHead(202, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'accepted' }));
      } catch (err) {
        console.error('Error processing message:', err);
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
      }
    });

    return;
  }

  // Health check endpoint
  if (req.url === '/health' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', activeSessions: sessions.size }));
    return;
  }

  // 404
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
});

// Start server
startGitHubServer();

server.listen(PORT, SERVER_HOST, () => {
  console.log(`GitHub MCP Wrapper running on http://${SERVER_HOST}:${PORT}`);
  console.log(`SSE endpoint: http://localhost:${PORT}/sse`);
  console.log(`Messages endpoint: http://localhost:${PORT}/messages`);
});

process.on('SIGTERM', () => {
  console.log('Received SIGTERM, shutting down...');
  if (serverProcess) {
    serverProcess.kill();
  }
  server.close(() => {
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('Received SIGINT, shutting down...');
  if (serverProcess) {
    serverProcess.kill();
  }
  server.close(() => {
    process.exit(0);
  });
});
