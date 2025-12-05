#!/usr/bin/env node

/**
 * Stdio-to-TCP Adapter for MCP Server
 *
 * This adapter runs the MCP server subprocess and exposes it over a TCP port.
 * This solves the docker-exec stdio piping issue by allowing network-based communication.
 *
 * Usage: PORT=5000 node stdio-adapter.js python -u /app/server.py
 */

const net = require('net');
const { spawn } = require('child_process');

const PORT = process.env.PORT || 5000;
const args = process.argv.slice(2);

if (args.length === 0) {
  console.error('Usage: PORT=5000 node stdio-adapter.js <command> [args...]');
  process.exit(1);
}

const command = args[0];
const cmdArgs = args.slice(1);

console.log(`[Adapter] Starting server: ${command} ${cmdArgs.join(' ')}`);
console.log(`[Adapter] Listening on port ${PORT}`);

// Start the MCP server subprocess
const serverProcess = spawn(command, cmdArgs, {
  stdio: ['pipe', 'pipe', 'pipe'],
  shell: false
});

serverProcess.on('error', (error) => {
  console.error(`[Adapter] Failed to start server: ${error.message}`);
  process.exit(1);
});

serverProcess.stderr.on('data', (data) => {
  console.error(`[Server Error] ${data.toString().trim()}`);
});

serverProcess.on('exit', (code) => {
  console.log(`[Adapter] Server exited with code ${code}`);
  process.exit(code || 1);
});

// Create TCP server that forwards to stdio
const server = net.createServer((socket) => {
  const clientId = Math.random().toString(36).substr(2, 9);
  console.log(`[Adapter] Client ${clientId} connected`);

  // Forward data from client to server subprocess stdin
  socket.on('data', (data) => {
    serverProcess.stdin.write(data);
  });

  // Forward data from server subprocess stdout to client
  serverProcess.stdout.on('data', (data) => {
    try {
      socket.write(data);
    } catch (error) {
      console.error(`[Adapter] Failed to write to client: ${error.message}`);
    }
  });

  socket.on('end', () => {
    console.log(`[Adapter] Client ${clientId} disconnected`);
  });

  socket.on('error', (error) => {
    console.error(`[Adapter] Socket error: ${error.message}`);
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[Adapter] Listening on 0.0.0.0:${PORT}`);
});

process.on('SIGTERM', () => {
  console.log('[Adapter] Shutting down');
  server.close();
  serverProcess.kill();
  process.exit(0);
});
