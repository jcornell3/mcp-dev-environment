/**
 * Simple MCP Test Server - No Dependencies
 * Uses Node.js built-in http module
 */

const http = require('http');
const url = require('url');
const { randomUUID } = require('crypto');

const PORT = 3000;
const API_TOKEN = 'test-token-123';

let sseClients = new Set();

const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;

  console.log(`[${new Date().toISOString()}] ${req.method} ${pathname}`);

  // Check authentication
  const authHeader = req.headers.authorization || '';
  const token = authHeader.replace(/^Bearer\s+/i, '');

  if (pathname !== '/health' && (!token || token !== API_TOKEN)) {
    console.log(`  ✗ Unauthorized (token: ${token})`);
    res.writeHead(401, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Unauthorized' }));
    return;
  }

  // Health check (no auth required)
  if (pathname === '/health' && req.method === 'GET') {
    console.log('  ✓ Health check');
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      connectedClients: sseClients.size
    }));
    return;
  }

  // SSE endpoint
  if (pathname === '/sse' && req.method === 'GET') {
    console.log('  → SSE connection opened');
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*'
    });

    sseClients.add(res);

    // Send connection message
    const msg = {
      jsonrpc: '2.0',
      id: randomUUID(),
      result: {
        status: 'connected',
        timestamp: new Date().toISOString(),
        connectedClients: sseClients.size
      }
    };
    res.write(`data: ${JSON.stringify(msg)}\n\n`);

    // Keep-alive
    const keepAlive = setInterval(() => {
      res.write(': keep-alive\n');
    }, 30000);

    req.on('close', () => {
      console.log('  ← SSE connection closed');
      sseClients.delete(res);
      clearInterval(keepAlive);
      res.end();
    });

    req.on('error', (error) => {
      console.log(`  ! SSE error: ${error.message}`);
      sseClients.delete(res);
      clearInterval(keepAlive);
      res.end();
    });

    return;
  }

  // Messages endpoint
  if (pathname === '/messages' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });

    req.on('end', () => {
      try {
        const request = JSON.parse(body);
        console.log(`  → Request: ${request.method} (id: ${request.id})`);

        // Send receipt
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          jsonrpc: '2.0',
          id: request.id,
          result: { status: 'received', timestamp: new Date().toISOString() }
        }));

        // Broadcast response via SSE
        setTimeout(() => {
          const response = {
            jsonrpc: '2.0',
            id: request.id,
            result: {
              method: request.method,
              processed: true,
              timestamp: new Date().toISOString(),
              message: `Echo: ${JSON.stringify(request.params || {})}`,
              connectedClients: sseClients.size
            }
          };

          for (const client of sseClients) {
            client.write(`data: ${JSON.stringify(response)}\n\n`);
          }
          console.log(`  ← Response sent: ${request.method} (id: ${request.id})`);
        }, 100);
      } catch (error) {
        console.log(`  ! Parse error: ${error.message}`);
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Invalid JSON' }));
      }
    });
    return;
  }

  // 404
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    error: 'Not Found',
    message: `Endpoint ${req.method} ${pathname} not found`
  }));
});

server.listen(PORT, () => {
  console.log('');
  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║         MCP Test Server (No Dependencies)                  ║');
  console.log('╚════════════════════════════════════════════════════════════╝');
  console.log('');
  console.log(`📡 Server running on http://localhost:${PORT}`);
  console.log(`🔐 API Token: ${API_TOKEN}`);
  console.log('');
  console.log('🔌 Endpoints:');
  console.log(`   GET  /sse              → SSE stream`);
  console.log(`   POST /messages         → Request handler`);
  console.log(`   GET  /health           → Health check (no auth)`);
  console.log('');
  console.log('🚀 Ready for testing!');
  console.log('');
});

process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down...');
  for (const client of sseClients) {
    client.end();
  }
  process.exit(0);
});
