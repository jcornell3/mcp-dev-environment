# Power Strip Architecture: Quick Reference

**Status**: Active
**Active Servers**: 4 (math, santa-clara, youtube-transcript, youtube-to-mp3)
**Ready for Expansion**: 1 (github-remote on port 3005)

## Port Allocation Registry

| Service Name | Container Port | Host Port | URL Endpoint | Auth Token |
|---|---|---|---|---|
| github-remote | 3000 | 3000 | http://localhost:3000/sse | `GITHUB_PERSONAL_ACCESS_TOKEN` |
| math-server | 3000 | 3001 | http://localhost:3001/sse | `BRIDGE_API_TOKEN` |
| santa-clara | 3000 | 3002 | http://localhost:3002/sse | `BRIDGE_API_TOKEN` |
| youtube-transcript | 3000 | 3003 | http://localhost:3003/sse | `BRIDGE_API_TOKEN` |
| youtube-to-mp3 | 3000 | 3004 | http://localhost:3004/sse | `BRIDGE_API_TOKEN` |

**Note**: All containers listen on internal port 3000. Docker Compose maps each to unique host port.

## Docker Compose Structure

```yaml
services:
  # Layer 1: Core MCP Servers (No exposed ports - internal communication only)
  math:
    build: ./servers/math
    environment:
      - MCP_API_KEY=${MCP_API_KEY}

  santa-clara:
    build: ./servers/santa-clara
    environment:
      - MCP_API_KEY=${MCP_API_KEY}

  # ... (youtube-transcript, youtube-to-mp3 follow same pattern)

  # Layer 2: Bridge Servers (HTTP/SSE - expose on unique ports)
  bridge-math:
    build: ./servers/universal-cloud-connector-test
    ports:
      - "${BRIDGE_MATH_PORT:-3001}:3000"
    environment:
      - PORT=3000
      - API_TOKEN=${BRIDGE_API_TOKEN}
      - TARGET_SERVER=math
    command: node /app/real-test-bridge.js

  # ... (bridge-santa-clara, bridge-youtube-transcript, bridge-youtube-to-mp3 follow same pattern)
```

## Claude Desktop Config Pattern

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
    }
    // ... repeat for 3003, 3004, 3005
  }
}
```

## Deployment Strategy

### Local Development
```bash
cd /home/jcornell/mcp-dev-environment
docker-compose up -d  # All 5 servers start
# Claude Desktop connects to localhost:300X
```

### Production (Hetzner/VPS)
```bash
scp -r ~/mcp-dev-environment user@server:/opt/
ssh user@server
cd /opt/mcp-dev-environment
docker-compose up -d  # Start all services

# Optional: Configure reverse proxy
# github.api.my-vps.com → localhost:3000
# math.api.my-vps.com → localhost:3001
# ... etc
```

## Key Differences from Original Bridge Architecture

| Aspect | Original Bridge | Current (Power Strip) |
|---|---|---|
| **Entry Point** | 1 bridge on port 3000 | 5 bridges on ports 3000-3005 |
| **Server Selection** | Dynamic via `/route` endpoint | Static via Claude config |
| **Server Count** | 1 active at a time | All active simultaneously |
| **Restart Required** | Yes (to switch servers) | No (just select tool) |
| **Container Count** | 1 bridge + 1 active server | 5 bridges + 5 servers |
| **Memory Overhead** | Lower | Higher (baseline) |
| **Configuration** | Single bridge entry | Multiple bridge entries |
| **Scalability** | Universal design | Specific implementation |

**Chosen for**: Simplicity, speed of development, simultaneous operation

## Configuration Files

### Files to Update

- **`.env`** — Server-specific environment variables
  ```bash
  MCP_API_KEY=default-api-key
  BRIDGE_API_TOKEN=bridge-default-secret
  BRIDGE_MATH_PORT=3001
  BRIDGE_SANTA_CLARA_PORT=3002
  # ... etc
  ```

- **`docker-compose.yml`** — Service definitions and port mappings
  - Layer 1: MCP server definitions
  - Layer 2: Bridge server definitions (exposes ports)

- **`claude_desktop_config.json`** — Claude Desktop MCP server configuration
  - Located in `%APPDATA%\Claude\` (Windows) or `~/Library/Application Support/Claude/` (macOS)
  - Contains 5 server entries, each pointing to unique port

### Files for Reference

- **`.env.example`** — Template for `.env` file
- **`ADDITIVE_DOCKER_SETUP.md`** — Comprehensive architecture guide
- **`POWER_STRIP_QUICK_REFERENCE.md`** — This file

## Starting & Monitoring

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# Health check (all bridges)
for port in 3001 3002 3003 3004 3005; do
  echo "Port $port:"
  curl -s http://localhost:$port/health | jq .
done

# View logs
docker-compose logs -f                    # All
docker-compose logs -f bridge-math        # Specific bridge
docker-compose logs -f math               # Specific backend

# Stop all
docker-compose down

# Rebuild (no cache)
docker-compose build --no-cache
```

## Expanding the Setup

To add a new server (e.g., `new-service`):

1. **Create server directory**: `servers/new-service/` with Dockerfile
2. **Add to docker-compose.yml** (Layer 1):
   ```yaml
   new-service:
     build: ./servers/new-service
     environment:
       - MCP_API_KEY=${MCP_API_KEY}
   ```
3. **Add bridge to docker-compose.yml** (Layer 2):
   ```yaml
   bridge-new-service:
     build: ./servers/universal-cloud-connector-test
     ports:
      - "${BRIDGE_NEW_SERVICE_PORT:-3006}:3000"
     environment:
      - PORT=3000
      - API_TOKEN=${BRIDGE_API_TOKEN}
      - TARGET_SERVER=new-service
     volumes:
      - /var/run/docker.sock:/var/run/docker.sock
   ```
4. **Add to .env**:
   ```bash
   BRIDGE_NEW_SERVICE_PORT=3006
   ```
5. **Add to claude_desktop_config.json**:
   ```json
   "new-service-bridge": {
     "bundlePath": "...",
     "config": {
       "server_url": "http://localhost:3006/sse",
       "api_token": "bridge-default-secret"
     }
   }
   ```
6. **Restart**:
   ```bash
   docker-compose build --no-cache
   docker-compose down && docker-compose up -d
   ```

## Architecture Trade-offs

### ✅ Advantages
- All servers run simultaneously (no cold start)
- Explicit port mapping (easy to understand)
- Independent failures (one crash doesn't affect others)
- Easier debugging (direct container-to-port mapping)
- Faster development iteration

### ❌ Disadvantages
- Higher memory footprint (10 containers vs. 2)
- More ports to manage (3001-3005 allocated)
- Manual configuration updates needed
- No dynamic routing (static port assignments)
- Monitoring complexity (5 endpoints to check)

## Common Commands

```bash
# Run everything
docker-compose up -d

# Check everything is running
docker-compose ps

# See all logs
docker-compose logs -f

# Stop everything
docker-compose down

# Rebuild everything
docker-compose build --no-cache

# Rebuild one service
docker-compose build --no-cache math

# Restart one bridge
docker-compose restart bridge-math

# Get into a container
docker-compose exec math bash

# Follow specific service logs
docker-compose logs -f math

# Remove stopped containers
docker-compose rm

# Remove everything including images
docker-compose down -v --remove-orphans
```

## Health Monitoring

Each bridge exposes `/health` endpoint:

```bash
curl -s http://localhost:3001/health | jq .
# Output:
# {
#   "status": "healthy",
#   "timestamp": "2025-12-04T18:16:21.913Z",
#   "connectedClients": 0,
#   "targetServer": "math"
# }
```

Use this for:
- Monitoring dashboards
- Load balancer health checks
- Alerting systems
- Status pages

---

**Last Updated**: December 4, 2025
**Version**: 1.0
