# Additive Docker Setup: The "Power Strip" Architecture

**Status**: Active
**Last Updated**: December 4, 2025
**Version**: 1.0

## Overview

Instead of running one MCP server at a time and swapping between them, this setup runs **all 5 MCP servers simultaneously** on a single host using a **Port Offset Strategy**. Think of it as a "Power Strip" — the host provides multiple sockets (ports), each connected to a different backend server.

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│              Claude Desktop (Host)                      │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │       Universal Connector (MCP Bundle)           │  │
│  │  Configured for 5 servers, each on unique port  │  │
│  └──────────────────────────────────────────────────┘  │
│                      │                                  │
│   ┌──────────────────┼──────────────────┐              │
│   ▼                  ▼                   ▼              │
│ :3001             :3002               :3003    :3004   │
│                                                 :3005   │
└─────────────────────────────────────────────────────────┘
   │                 │                      │       │       │
   │ localhost       │ localhost            │       │       │
   │                 │                      │       │       │
   ▼                 ▼                      ▼       ▼       ▼
┌──────┐         ┌──────────┐        ┌────────┐ ┌─────┐ ┌──────────┐
│Math  │         │Santa     │        │YouTube │ │YT   │ │GitHub    │
│Server│         │Clara     │        │Trans   │ │MP3  │ │Remote    │
└──────┘         └──────────┘        └────────┘ └─────┘ └──────────┘
```

---

## 1. The Concept

### Host as "Power Strip"
- The host machine exposes **5 different ports** (3001-3005)
- Each port is mapped to a unique backend server via Docker Compose
- Clients can connect to different servers by changing only the port number

### Containers in Background
- All MCP servers run **simultaneously** in Docker containers
- Each container listens on internal port **3000**
- Docker maps each container's internal 3000 to a unique external port
- No container conflicts because each has its own isolated port

### Client Configuration
- Claude Desktop runs **multiple instances** of the Universal Cloud Connector
- Each instance is configured to point to a different port
- Switching between servers requires no container restarts — just change the active tool

---

## 2. Port Allocation Registry

All services are standardized to prevent conflicts between environments.

| Service | Internal Port | External Port | URL Endpoint | Auth Token |
|---------|---------------|---------------|-----|---|
| **math** | 3000 | 3001 | `http://localhost:3001/sse` | `bridge-default-secret` |
| **santa-clara** | 3000 | 3002 | `http://localhost:3002/sse` | `bridge-default-secret` |
| **youtube-transcript** | 3000 | 3003 | `http://localhost:3003/sse` | `bridge-default-secret` |
| **youtube-to-mp3** | 3000 | 3004 | `http://localhost:3004/sse` | `bridge-default-secret` |
| **github-remote** | 3000 | 3005 | `http://localhost:3005/sse` | `bridge-default-secret` |

### Notes
- **Internal Port**: What the container listens on (always 3000)
- **External Port**: What the host exposes to Claude Desktop
- **Port Range**: 3001-3005 (reserved for bridge servers)
- **Auth Token**: Shared across all bridges for simplicity; customize in `.env`

---

## 3. Configuration Reference

### Docker Compose Structure

The `docker-compose.yml` is organized into two layers:

#### Layer 1: Core MCP Servers (No exposed ports)
```yaml
services:
  math:
    build: ./servers/math
    environment:
      - MCP_API_KEY=${MCP_API_KEY}
    # No ports exposed - only accessed via bridge

  santa-clara:
    build: ./servers/santa-clara
    environment:
      - MCP_API_KEY=${MCP_API_KEY}

  youtube-transcript:
    build: ./servers/youtube-transcript
    environment:
      - MCP_API_KEY=${MCP_API_KEY}

  youtube-to-mp3:
    build: ./servers/youtube-to-mp3
    environment:
      - DOWNLOADS_DIR=/app/downloads
      - MCP_API_KEY=${MCP_API_KEY}
    volumes:
      - ${DOWNLOADS_DIR}:/app/downloads
```

#### Layer 2: Bridge Servers (HTTP/SSE, expose ports)
```yaml
  bridge-math:
    build: ./servers/universal-cloud-connector-test
    ports:
      - "${BRIDGE_MATH_PORT:-3001}:3000"
    depends_on:
      - math
    environment:
      - PORT=3000
      - API_TOKEN=${BRIDGE_API_TOKEN}
      - TARGET_SERVER=math
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: node /app/real-test-bridge.js

  bridge-santa-clara:
    build: ./servers/universal-cloud-connector-test
    ports:
      - "${BRIDGE_SANTA_CLARA_PORT:-3002}:3000"
    depends_on:
      - santa-clara
    environment:
      - PORT=3000
      - API_TOKEN=${BRIDGE_API_TOKEN}
      - TARGET_SERVER=santa-clara
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: node /app/real-test-bridge.js

  # ... Repeat for youtube-transcript (3003), youtube-to-mp3 (3004), github-remote (3005)
```

### Claude Desktop Configuration

Update `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "math-bridge": {
      "bundlePath": "/home/jcornell/universal-cloud-connector/universal-cloud-connector.mcpb",
      "config": {
        "server_url": "http://localhost:3001/sse",
        "api_token": "bridge-default-secret"
      }
    },
    "santa-clara-bridge": {
      "bundlePath": "/home/jcornell/universal-cloud-connector/universal-cloud-connector.mcpb",
      "config": {
        "server_url": "http://localhost:3002/sse",
        "api_token": "bridge-default-secret"
      }
    },
    "youtube-transcript-bridge": {
      "bundlePath": "/home/jcornell/universal-cloud-connector/universal-cloud-connector.mcpb",
      "config": {
        "server_url": "http://localhost:3003/sse",
        "api_token": "bridge-default-secret"
      }
    },
    "youtube-to-mp3-bridge": {
      "bundlePath": "/home/jcornell/universal-cloud-connector/universal-cloud-connector.mcpb",
      "config": {
        "server_url": "http://localhost:3004/sse",
        "api_token": "bridge-default-secret"
      }
    },
    "github-remote-bridge": {
      "bundlePath": "/home/jcornell/universal-cloud-connector/universal-cloud-connector.mcpb",
      "config": {
        "server_url": "http://localhost:3005/sse",
        "api_token": "bridge-default-secret"
      }
    }
  }
}
```

### Environment Variables (`.env`)

```bash
# API Keys & Authentication
MCP_API_KEY=default-api-key
BRIDGE_API_TOKEN=bridge-default-secret
GITHUB_PERSONAL_ACCESS_TOKEN=<your-github-token>

# Bridge Port Configuration
BRIDGE_MATH_PORT=3001
BRIDGE_SANTA_CLARA_PORT=3002
BRIDGE_YOUTUBE_TRANSCRIPT_PORT=3003
BRIDGE_YOUTUBE_TO_MP3_PORT=3004
BRIDGE_GITHUB_REMOTE_PORT=3005

# Service-Specific Configuration
DOWNLOADS_DIR=/mnt/c/Users/jcorn/Downloads
```

---

## 4. Usage

### Starting All Services

```bash
# From /home/jcornell/mcp-dev-environment

# Load environment variables (optional, docker-compose reads .env automatically)
source .env

# Start all services in background
docker-compose up -d

# Verify all services are running
docker-compose ps
```

**Expected Output:**
```
NAME                                  IMAGE                           PORTS
mcp-dev-environment-bridge-math-1     ...                             0.0.0.0:3001->3000/tcp
mcp-dev-environment-bridge-santa-clara-1  ...                         0.0.0.0:3002->3000/tcp
mcp-dev-environment-bridge-youtube-transcript-1  ...                  0.0.0.0:3003->3000/tcp
mcp-dev-environment-bridge-youtube-to-mp3-1  ...                      0.0.0.0:3004->3000/tcp
mcp-dev-environment-math-1            ...                             (no port)
mcp-dev-environment-santa-clara-1     ...                             (no port)
mcp-dev-environment-youtube-transcript-1  ...                         (no port)
mcp-dev-environment-youtube-to-mp3-1  ...                             (no port)
```

### Stopping All Services

```bash
docker-compose down
```

### Health Checks

Each bridge exposes a `/health` endpoint for monitoring:

```bash
# Check all bridges
for port in 3001 3002 3003 3004 3005; do
  echo "=== Bridge on port $port ==="
  curl -s http://localhost:$port/health | jq .
done
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f bridge-math
docker-compose logs -f math

# Follow only errors
docker-compose logs -f 2>&1 | grep -i error
```

### Rebuilding Images

```bash
# Rebuild all images (no cache)
docker-compose build --no-cache

# Rebuild only one service
docker-compose build --no-cache math
docker-compose build --no-cache bridge-math

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 5. Deployment Variants

### Local Development (Current Setup)

**Environment**: WSL/Linux running Docker Desktop
**Execution**:
```bash
docker-compose up -d
# All services start on localhost:3001-3005
```

**Claude Desktop Config**: Points to `http://localhost:300X/sse`

### Production (Hetzner / VPS)

**Environment**: Remote server with Docker
**Execution**:
```bash
# Copy repo to Hetzner
scp -r ~/mcp-dev-environment user@server:/opt/

# SSH and start services
ssh user@server
cd /opt/mcp-dev-environment
docker-compose up -d
```

**DNS/Reverse Proxy Setup** (Optional - for domain names):
```bash
# Using Caddy or Nginx to map domains
math.api.example.com -> localhost:3001
santa-clara.api.example.com -> localhost:3002
youtube-transcript.api.example.com -> localhost:3003
youtube-to-mp3.api.example.com -> localhost:3004
github-remote.api.example.com -> localhost:3005
```

**Claude Desktop Config** (Remote):
```json
{
  "mcpServers": {
    "math-bridge": {
      "bundlePath": "...",
      "config": {
        "server_url": "https://math.api.example.com/sse",
        "api_token": "bridge-default-secret"
      }
    }
    // ... repeat for other domains
  }
}
```

---

## 6. Architecture Trade-offs

### Advantages ✅
- **Simultaneous Operation**: All servers run at once — no restart required to switch
- **Simplified Debugging**: Direct port mapping makes troubleshooting easier
- **Independent Failures**: One server crash doesn't affect others
- **Scalability**: Easy to add new servers by adding bridge entries
- **Development Speed**: Faster iteration (no docker-compose restart between tool changes)

### Disadvantages ❌
- **Port Overhead**: Requires 10 containers (5 servers + 5 bridges) vs. 1 bridge
- **Memory Usage**: Higher baseline memory footprint
- **Configuration Complexity**: Multiple config entries instead of single bridge
- **Manual Port Management**: Must track port allocations to avoid conflicts
- **Monitoring**: Need to health-check 5 separate endpoints

---

## 7. Troubleshooting

### Bridge Won't Start
```bash
# Check if port is already in use
lsof -i :3001
# Kill conflicting process or change port in .env

# Check bridge logs
docker-compose logs bridge-math
```

### Backend Server Not Responding
```bash
# Check if backend container is running
docker-compose ps math

# View backend logs
docker-compose logs math

# Manually test the server
docker-compose exec -it math python -u /app/server.py
```

### Port Already in Use
```bash
# Find what's using the port
sudo lsof -i :3001

# Option 1: Kill the process
kill -9 <PID>

# Option 2: Change port in .env
BRIDGE_MATH_PORT=3011
docker-compose down && docker-compose up -d
```

### Docker Compose Version Issues
```bash
# Remove the obsolete `version` key from docker-compose.yml
# Change: version: '3.8'
# To: (remove the line entirely)

# This is a Docker Compose v2 specification
```

---

## 8. Architecture Documentation

For historical context and the original bridge-based architecture, see:

- [universal-cloud-connector/docs/ARCHITECTURE.md](https://github.com/jcornell3/universal-cloud-connector/blob/master/docs/ARCHITECTURE.md)
  - Original UCC bridge design (preserved for reference)
  - Deployment variant explanation (why we chose direct architecture)
  - Comparison table (bridge vs. direct approaches)

---

## 9. Next Steps

### Expanding the Setup

1. **Add a New Server**
   - Create `servers/new-server/` with Dockerfile and MCP implementation
   - Add `new-server` service to `docker-compose.yml`
   - Add `bridge-new-server` service with dedicated port (e.g., 3006)
   - Add entry to `claude_desktop_config.json`
   - Update `.env` with `BRIDGE_NEW_SERVER_PORT=3006`

2. **Customize Bridge Authentication**
   - Generate unique `BRIDGE_API_TOKEN` in `.env`
   - Update all bridge entries in `claude_desktop_config.json`
   - Restart bridges: `docker-compose restart bridge-math bridge-santa-clara ...`

3. **Monitor Production Deployment**
   - Set up logging aggregation (ELK, CloudWatch)
   - Create alerts for bridge health endpoint failures
   - Implement load balancer if needed (Nginx, HAProxy)

---

## 10. Status

**Current Deployment**: All 4 core servers + bridges running and healthy
**Health Checks**: ✅ math (3001), ✅ santa-clara (3002), ✅ youtube-transcript (3003), ✅ youtube-to-mp3 (3004)
**Configuration**: Complete and documented
**Testing**: Verified connectivity through health endpoints

---

## File Inventory

- **`docker-compose.yml`** — Service definitions with port mappings
- **`.env`** — Environment variables (API keys, ports)
- **`.env.example`** — Template for `.env` configuration
- **`claude_desktop_config.json`** — Claude Desktop bridge entries (in user AppData)
- **`servers/*/Dockerfile`** — Container definitions for each MCP server
- **`servers/universal-cloud-connector-test/real-test-bridge.js`** — Bridge implementation
- **`ADDITIVE_DOCKER_SETUP.md`** — This document

---

**Version History**
- **1.0** (2025-12-04) — Initial implementation of Additive Docker setup with 4 active servers

