# MCP Development Environment - Active Configuration

## Summary
This document describes the currently running MCP development environment to avoid port conflicts and resource collisions with other projects.

---

## Docker Containers Running

### Container 1: Nginx Reverse Proxy
- **Container name:** `mcp-dev-environment-nginx-1`
- **Image:** Custom nginx:alpine
- **Network:** `mcp-network` (bridge, subnet: 172.28.0.0/16)
- **Status:** Running

### Container 2: Santa Clara MCP Server
- **Container name:** `mcp-dev-environment-santa-clara-1`
- **Image:** Custom Python Flask app
- **Network:** `mcp-network` (bridge, subnet: 172.28.0.0/16)
- **Status:** Running

---

## Port Usage

### Host Ports (Exposed to Windows/WSL)
- **8443** - HTTPS (Nginx reverse proxy with SSL/TLS)
  - Bound to: `127.0.0.1:8443` (localhost only)
  - Protocol: HTTPS (self-signed certificate via mkcert)
  - Endpoints:
    - `https://localhost:8443/` - Root endpoint
    - `https://localhost:8443/health` - Health check
    - `https://localhost:8443/santa-clara/*` - Santa Clara MCP routes

### Container Internal Ports (Not exposed to host)
- **443** - Nginx internal HTTPS listener (inside nginx container)
- **80** - Nginx internal HTTP listener (inside nginx container)
- **8000** - Santa Clara MCP server (inside santa-clara container)

**No other host ports are in use by this environment.**

---

## Network Configuration

### Docker Network
- **Network name:** `mcp-network`
- **Driver:** bridge
- **Subnet:** 172.28.0.0/16
- **Scope:** Local to this docker-compose project

### DNS/Hostnames (Internal to Docker network)
- `nginx` - Resolves to nginx container
- `santa-clara` - Resolves to santa-clara-mcp container

---

## File System Usage

### WSL Paths
- **Project root:** `~/mcp-dev-environment`
- **Logs:** `~/mcp-dev-environment/logs/`
- **Certificates:** `~/mcp-dev-environment/certs/`
- **Data:** `~/mcp-dev-environment/data/`

### Docker Volumes
- Named volumes: `mcp-dev-environment_logs`, `mcp-dev-environment_data`
- Bind mounts:
  - `./certs:/etc/nginx/certs:ro` (nginx container)
  - `./logs:/var/log/nginx` (nginx container)
  - `./logs:/app/logs` (santa-clara container)

---

## Resource Limits

### Santa Clara MCP Container
- **CPU:** 1.0 core limit
- **Memory:** 2GB limit

### Nginx Container
- **CPU:** No limit
- **Memory:** No limit

---

## Management Commands

### Start/Stop
```bash
cd ~/mcp-dev-environment
make start   # Start all services
make stop    # Stop all services
make restart # Restart all services
```

### Check Status
```bash
docker compose ps                    # Container status
curl -k https://localhost:8443/      # Test endpoint
curl -k https://localhost:8443/health # Health check
```

---

## Avoiding Conflicts

### When Starting Other Projects:

**Ports to avoid:**
- ❌ **8443** - Already in use by MCP nginx proxy

**Safe ports to use:**
- ✅ **3000-8442** - Available
- ✅ **8444-9000** - Available
- ✅ **9001+** - Available

**Docker networks to avoid:**
- ❌ **mcp-network**
- ❌ **Subnet 172.28.0.0/16**

**Safe networks:**
- ✅ Create your own bridge network with different subnet (e.g., 172.29.0.0/16)

**Container names to avoid:**
- ❌ `mcp-dev-environment-*`
- ❌ `santa-clara-*`

---

## Quick Reference

**Is MCP environment running?**
```bash
docker compose -f ~/mcp-dev-environment/docker-compose.yml ps
```

**Stop MCP environment temporarily:**
```bash
cd ~/mcp-dev-environment && make stop
```

**Restart MCP environment:**
```bash
cd ~/mcp-dev-environment && make start
```

---

## GitHub Repository
- **URL:** https://github.com/jcornell3/mcp-dev-environment
- **Branch:** main
- **Visibility:** Public

---

## Last Updated
November 29, 2025
