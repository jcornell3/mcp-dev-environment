#!/usr/bin/env node

/**
 * Real Test Bridge Server
 * Bridges HTTP/SSE to an actual Docker-based MCP server via stdio
 */

const http = require('http');
const https = require('https');
const { spawn } = require('child_process');

const PORT = process.env.PORT || 3000;
const TARGET_SERVER = process.env.TARGET_SERVER || 'math'; // Can be 'math' or 'santa-clara'

let serverProcess = null;
let connectedClients = new Map(); // Map of clientId -> { res, active }
let sseBroadcastQueue = []; // Queue of responses to broadcast via SSE

// Start the target MCP server via docker exec
function startTargetServer() {
  console.log(`[Bridge] Starting target server: ${TARGET_SERVER}`);

  const containerName = `mcp-dev-environment-${TARGET_SERVER}-1`;
  const command = 'docker';
  const args = [
    'exec',
    '-i',
    containerName,
    'python',
    '-u',
    '/app/server.py'
  ];

  serverProcess = spawn(command, args, {
    stdio: ['pipe', 'pipe', 'pipe']
  });

  serverProcess.stderr.on('data', (data) => {
    console.error(`[Target Server Error] ${data}`);
  });

  serverProcess.on('exit', (code) => {
    console.log(`[Bridge] Target server exited with code ${code}`);
    serverProcess = null;
    startTargetServer(); // Restart on exit
  });

  // Send initialize message immediately
  setTimeout(() => {
    const initMessage = {
      jsonrpc: '2.0',
      id: 0,
      method: 'initialize',
      params: {
        protocolVersion: '2025-06-18',
        capabilities: {},
        clientInfo: {
          name: 'test-bridge',
          version: '1.0'
        }
      }
    };
    console.log('[Bridge] Sending initialize to target server');
    serverProcess.stdin.write(JSON.stringify(initMessage) + '\n');
  }, 500);

  return serverProcess;
}

// Send JSON-RPC request to target server and get response
function forwardToTargetServer(request) {
  return new Promise((resolve, reject) => {
    if (!serverProcess) {
      reject(new Error('Target server not ready'));
      return;
    }

    let buffer = '';
    const responseHandler = (data) => {
      buffer += data.toString();
      const lines = buffer.split('\n');

      // Keep the last incomplete line in the buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.trim()) {
          try {
            const response = JSON.parse(line);
            // Match responses by id if available, otherwise take first response
            if (response.id === request.id || !request.id) {
              serverProcess.stdout.removeListener('data', responseHandler);
              resolve(response);
              return;
            }
          } catch (e) {
            // Ignore parse errors, might be partial data
            console.error(`[Bridge] Parse error: ${e.message}`);
          }
        }
      }
    };

    // Listen for response
    serverProcess.stdout.on('data', responseHandler);

    // Send request to target server
    try {
      serverProcess.stdin.write(JSON.stringify(request) + '\n');
    } catch (error) {
      serverProcess.stdout.removeListener('data', responseHandler);
      reject(new Error(`Failed to write to stdin: ${error.message}`));
      return;
    }

    // Timeout after 10 seconds
    const timeoutId = setTimeout(() => {
      serverProcess.stdout.removeListener('data', responseHandler);
      reject(new Error('Target server timeout'));
    }, 10000);

    // Clean up timeout if we resolve
    const originalResolve = resolve;
    resolve = (value) => {
      clearTimeout(timeoutId);
      originalResolve(value);
    };
  });
}

// Create HTTP server with SSE support
const server = http.createServer(async (req, res) => {
  console.log(`[Bridge] ${req.method} ${req.url}`);

  // Health check endpoint
  if (req.url === '/health' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      connectedClients: connectedClients.size,
      targetServer: TARGET_SERVER
    }));
    return;
  }

  // SSE endpoint
  if (req.url === '/sse' && req.method === 'GET') {
    const token = req.headers.authorization?.replace('Bearer ', '');

    if (token !== process.env.API_TOKEN) {
      res.writeHead(401, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Unauthorized' }));
      return;
    }

    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*'
    });

    const clientId = Math.random().toString(36);
    connectedClients.set(clientId, { res, active: true });
    console.log(`[Bridge] SSE client connected: ${clientId} (total: ${connectedClients.size})`);

    // Send initial connection message
    res.write(`data: ${JSON.stringify({ status: 'connected', timestamp: new Date().toISOString(), connectedClients: connectedClients.size })}\n\n`);

    // Send any queued messages
    while (sseBroadcastQueue.length > 0) {
      const queuedMessage = sseBroadcastQueue.shift();
      res.write(`data: ${JSON.stringify(queuedMessage)}\n\n`);
      console.log(`[Bridge] Sent queued message to ${clientId}`);
    }

    // Handle client disconnect
    req.on('close', () => {
      const client = connectedClients.get(clientId);
      if (client) {
        client.active = false;
      }
      connectedClients.delete(clientId);
      console.log(`[Bridge] SSE client disconnected: ${clientId} (total: ${connectedClients.size})`);
    });

    // Keep connection alive
    const keepalive = setInterval(() => {
      if (!res.writableEnded) {
        res.write(': keepalive\n\n');
      }
    }, 30000);

    res.on('close', () => {
      clearInterval(keepalive);
    });

    return;
  }

  // Helper function to broadcast responses via SSE
  function broadcastViaSSE(message) {
    let sent = false;
    for (const [clientId, client] of connectedClients.entries()) {
      if (client.active && !client.res.writableEnded) {
        try {
          client.res.write(`data: ${JSON.stringify(message)}\n\n`);
          console.log(`[Bridge] Sent response via SSE to client ${clientId}`);
          sent = true;
        } catch (error) {
          console.error(`[Bridge] Failed to send to client ${clientId}: ${error.message}`);
          client.active = false;
        }
      }
    }
    if (!sent) {
      console.log('[Bridge] No active SSE clients, queuing response');
      sseBroadcastQueue.push(message);
    }
  }

  // Messages endpoint - HTTP POST receives requests, sends responses via SSE
  if (req.url === '/messages' && req.method === 'POST') {
    const token = req.headers.authorization?.replace('Bearer ', '');

    if (token !== process.env.API_TOKEN) {
      res.writeHead(401, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Unauthorized' }));
      return;
    }

    let body = '';
    req.on('data', (chunk) => {
      body += chunk.toString();
    });

    req.on('end', async () => {
      try {
        const request = JSON.parse(body);
        console.log(`[Bridge] Forwarding to target: ${request.method} (id: ${request.id})`);

        // Forward request to target server
        const response = await forwardToTargetServer(request);

        // Send response via SSE to all connected clients
        console.log(`[Bridge] Got response from target server, broadcasting via SSE`);
        broadcastViaSSE(response);

        // Respond with 202 Accepted to indicate async response will be sent via SSE
        res.writeHead(202, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'accepted', message: 'Response will be sent via SSE' }));
      } catch (error) {
        console.error('[Bridge] Error:', error);
        const errorResponse = {
          jsonrpc: '2.0',
          error: { code: -32603, message: 'Internal error', data: error.message }
        };
        // Also try to send error via SSE
        broadcastViaSSE(errorResponse);

        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(errorResponse));
      }
    });
    return;
  }

  // 404
  res.writeHead(404);
  res.end('Not found');
});

// Start servers
startTargetServer();

server.listen(PORT, () => {
  console.log(`[Bridge] SSE bridge listening on port ${PORT}`);
  console.log(`[Bridge] Target server: ${TARGET_SERVER}`);
  console.log(`[Bridge] Health: http://localhost:${PORT}/health`);
  console.log(`[Bridge] SSE: http://localhost:${PORT}/sse`);
  console.log(`[Bridge] Messages: http://localhost:${PORT}/messages`);
});

process.on('SIGTERM', () => {
  console.log('[Bridge] Shutting down');
  server.close();
  if (serverProcess) {
    serverProcess.kill();
  }
  process.exit(0);
});
