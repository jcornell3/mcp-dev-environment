# Operational Notes: Power Strip Architecture

**Created**: December 4, 2025
**Status**: Active and Operational
**Maintained By**: Development Team

## Executive Summary

The Additive Docker Setup (Power Strip Architecture) is a multi-server deployment pattern where all 4 MCP servers run simultaneously with dedicated HTTP/SSE bridges on unique host ports (3001-3005). This eliminates cold-start delays, enables rapid switching between tools in Claude Desktop, and simplifies debugging through explicit port-to-service mappings.

---

## Deployment Quick Reference

### Daily Operations

**Start Services** (~ 10 seconds):
```bash
cd /home/jcornell/mcp-dev-environment
docker-compose up -d
```
All 8 containers will start. Check status with `docker-compose ps`.

**Stop Services**:
```bash
docker-compose down
```
Gracefully stops all containers and cleans up the network.

**Verify Health**:
```bash
for port in 3001 3002 3003 3004; do
  curl -s http://localhost:$port/health | jq .
done
```
All should return `{"status":"healthy",...}`.

**View Logs**:
```bash
docker-compose logs -f              # All containers
docker-compose logs -f bridge-math  # Specific bridge
docker-compose logs -f math         # Specific backend
```

### Maintenance

**Rebuild All Images** (when code changes):
```bash
docker-compose build --no-cache
docker-compose down && docker-compose up -d
```

**Rebuild Single Service**:
```bash
docker-compose build --no-cache math
docker-compose restart bridge-math
```

**Check Resource Usage**:
```bash
docker stats  # Shows CPU, memory, network stats in real-time
```

---

## Port Reference

**Exact Port Mapping**:

| Service | Host Port | Container Port | Claude Config | Notes |
|---------|-----------|------------------|---|---|
| math | 3001 | 3000 | math-bridge | Primary math tools |
| santa-clara | 3002 | 3000 | santa-clara-bridge | Property tax lookup |
| youtube-transcript | 3003 | 3000 | youtube-transcript-bridge | Video transcription |
| youtube-to-mp3 | 3004 | 3000 | youtube-to-mp3-bridge | Audio extraction |
| github-remote | 3005 | 3000 | github-remote-bridge | Reserved (not yet implemented) |

**Health Endpoints**: `http://localhost:300X/health` (where X = 1-5)

---

## Configuration Management

### Environment Variables (.env)

Critical variables for operation:

```bash
# Must be set correctly
MCP_API_KEY=default-api-key
BRIDGE_API_TOKEN=bridge-default-secret
DOWNLOADS_DIR=/mnt/c/Users/jcorn/Downloads

# Port assignments (change these to avoid conflicts)
BRIDGE_MATH_PORT=3001
BRIDGE_SANTA_CLARA_PORT=3002
BRIDGE_YOUTUBE_TRANSCRIPT_PORT=3003
BRIDGE_YOUTUBE_TO_MP3_PORT=3004
BRIDGE_GITHUB_REMOTE_PORT=3005
```

**If Ports Conflict**: Edit `.env` to use different ports (e.g., 3011, 3012, etc.), then restart.

### Claude Desktop Configuration

Located at: `%APPDATA%\Claude\claude_desktop_config.json`

Each server must have an entry like:
```json
"math-bridge": {
  "bundlePath": "/home/jcornell/universal-cloud-connector/universal-cloud-connector.mcpb",
  "config": {
    "server_url": "http://localhost:3001/sse",
    "api_token": "bridge-default-secret"
  }
}
```

**URL Pattern**: `http://localhost:300X/sse` (note the `/sse` path)
**Auth Token**: Must match `BRIDGE_API_TOKEN` in `.env`

---

## Common Issues & Solutions

### Bridge Not Responding

**Symptom**: `curl http://localhost:3001/health` returns "Connection refused"

**Fix**:
1. Check if port is allocated: `lsof -i :3001`
2. View bridge logs: `docker-compose logs bridge-math`
3. Restart bridge: `docker-compose restart bridge-math`
4. If port is in use, kill conflict: `kill -9 <PID>`
5. Full restart: `docker-compose down && docker-compose up -d`

### Backend Server Crashes

**Symptom**: Bridge is healthy but tools don't work

**Fix**:
1. Check backend logs: `docker-compose logs math`
2. Look for Python errors or resource issues
3. Rebuild container: `docker-compose build --no-cache math`
4. Restart: `docker-compose restart math`

### Claude Desktop Won't Connect

**Symptom**: "MCP server not available" in Claude Desktop

**Fix**:
1. Verify bridge is running: `docker-compose ps | grep bridge-math`
2. Test health: `curl http://localhost:3001/health`
3. Check config syntax in `claude_desktop_config.json` (JSON must be valid)
4. Verify URL: `http://localhost:300X/sse` (exact format required)
5. Check token in `.env` matches config file
6. Reload Claude Desktop or restart application

### Port Conflicts

**Symptom**: `docker-compose up` fails with "Port already allocated"

**Fix**:
```bash
# Find what's using the port
lsof -i :3001

# Option 1: Kill the process
kill -9 <PID>

# Option 2: Change port in .env
# Edit .env: BRIDGE_MATH_PORT=3011
docker-compose down && docker-compose up -d

# Update claude_desktop_config.json to match new port
```

---

## Scaling & Expansion

### Adding a New Server

To add a fifth server (e.g., `custom-tool`):

1. **Create the server** in `servers/custom-tool/`
2. **Add to docker-compose.yml** (Layer 1 - backend):
   ```yaml
   custom-tool:
     build: ./servers/custom-tool
     environment:
       - MCP_API_KEY=${MCP_API_KEY}
   ```

3. **Add bridge** (Layer 2 - HTTP/SSE):
   ```yaml
   bridge-custom-tool:
     build: ./servers/universal-cloud-connector-test
     ports:
       - "${BRIDGE_CUSTOM_TOOL_PORT:-3006}:3000"
     environment:
       - PORT=3000
       - API_TOKEN=${BRIDGE_API_TOKEN}
       - TARGET_SERVER=custom-tool
     volumes:
       - /var/run/docker.sock:/var/run/docker.sock
   ```

4. **Add to .env**:
   ```bash
   BRIDGE_CUSTOM_TOOL_PORT=3006
   ```

5. **Add to claude_desktop_config.json**:
   ```json
   "custom-tool-bridge": {
     "bundlePath": ".../universal-cloud-connector.mcpb",
     "config": {
       "server_url": "http://localhost:3006/sse",
       "api_token": "bridge-default-secret"
     }
   }
   ```

6. **Deploy**:
   ```bash
   docker-compose build --no-cache
   docker-compose down && docker-compose up -d
   ```

---

## Monitoring

### Health Status Dashboard

```bash
# One-liner health check
watch -n 5 "echo 'HEALTH STATUS' && for p in 3001 3002 3003 3004; do echo -n \"Port $p: \"; curl -s http://localhost:$p/health | jq -r .status; done"
```

### Container Status

```bash
# Watch all containers in real-time
watch docker-compose ps

# Check resource usage
docker stats --no-stream
```

### Log Aggregation

```bash
# View all logs with timestamps
docker-compose logs -f --timestamps

# Follow only error messages
docker-compose logs -f 2>&1 | grep -i error

# Tail last 50 lines of specific service
docker-compose logs -f --tail=50 bridge-math
```

---

## Backup & Recovery

### Backup Current State

```bash
# Backup docker-compose.yml
cp docker-compose.yml docker-compose.yml.backup

# Backup .env (CAUTION: contains secrets)
cp .env .env.backup

# Backup Claude config
cp %APPDATA%\Claude\claude_desktop_config.json claude_desktop_config.json.backup
```

### Recovery Procedure

```bash
# If docker-compose.yml is corrupted:
cp docker-compose.yml.backup docker-compose.yml
docker-compose build --no-cache
docker-compose up -d

# If .env is lost:
# Recreate from .env.example and update with your values
cp .env.example .env
# Edit .env with actual API keys and tokens
```

---

## Production Deployment

### Deploying to Hetzner/VPS

```bash
# 1. Copy repository to server
scp -r ~/mcp-dev-environment user@server.com:/opt/

# 2. SSH into server
ssh user@server.com

# 3. Navigate and start services
cd /opt/mcp-dev-environment
docker-compose up -d

# 4. (Optional) Set up reverse proxy
# Configure Nginx/Caddy to route subdomains to ports
# Example:
#   math.api.example.com  → localhost:3001
#   santa-clara.api.example.com → localhost:3002
#   youtube-transcript.api.example.com → localhost:3003
#   youtube-to-mp3.api.example.com → localhost:3004

# 5. Update Claude Desktop config to use domain names
#   "server_url": "https://math.api.example.com/sse"
```

### Environment-Specific Variables

Create separate `.env` files:
- `.env.local` — Development environment
- `.env.production` — Production environment

Use with: `docker-compose --env-file .env.production up -d`

---

## Security Notes

### API Token Management

⚠️ **Important**: The `BRIDGE_API_TOKEN` is shared across all bridges for simplicity. In production:

1. **Generate strong token**: Use `openssl rand -hex 32`
2. **Store securely**: Use Docker secrets or HashiCorp Vault
3. **Rotate regularly**: Plan for periodic token rotation
4. **Monitor usage**: Log all authentication attempts

### Port Exposure

⚠️ **Important**: Ports 3001-3005 expose the bridges directly. In production:

1. **Use firewall rules**: Only allow trusted IPs
2. **Run behind VPN**: Require VPN connection to access
3. **Use HTTPS**: Implement TLS/SSL termination at proxy layer
4. **Authenticate at proxy**: Add authentication before bridge

### Sensitive Data

- `GITHUB_PERSONAL_ACCESS_TOKEN`: Requires `.gitignore` (never commit)
- `DOWNLOADS_DIR`: Ensure proper file permissions on mounted directory
- Environment variables: Use secrets management in production

---

## Performance Tuning

### Memory Usage

```bash
# Check memory per container
docker stats --no-stream

# If high: Increase Docker memory limit
# For Windows/WSL: Adjust in Docker Desktop settings
# For Linux: No hard limit, but monitor with `docker stats`
```

### CPU Usage

```bash
# View CPU usage
docker stats

# If high on idle:
# - Check bridge logs for infinite loops
# - Check backend logs for cpu-intensive operations
# - Profile with: docker run --cpus=1.0 <container>
```

### Network Optimization

```bash
# Use host network mode (Linux only) for better throughput
# Edit docker-compose.yml:
# services:
#   math:
#     network_mode: "host"  # Shares host network namespace
```

---

## Documentation References

- **ADDITIVE_DOCKER_SETUP.md** — Comprehensive architecture guide
- **POWER_STRIP_QUICK_REFERENCE.md** — Quick lookup and examples
- **universal-cloud-connector ARCHITECTURE.md** — Bridge design patterns
- **YouTube-to-MP3 LESSONS_LEARNED.md** — Mount point debugging insights

---

## Support & Escalation

### Before Escalating

1. Check health endpoints for all bridges
2. Review logs: `docker-compose logs -f`
3. Verify .env and claude_desktop_config.json syntax
4. Try full restart: `docker-compose down && docker-compose up -d`
5. Check disk space: `df -h`
6. Check Docker daemon: `docker ps` (should return container list)

### Information to Include

When reporting issues:
```bash
# Gather debug information
echo "=== Docker Version ===" && docker --version
echo "=== Docker Compose Version ===" && docker-compose --version
echo "=== Container Status ===" && docker-compose ps
echo "=== Health Check ===" && for p in 3001 3002 3003 3004; do curl -s http://localhost:$p/health; done
echo "=== Recent Logs ===" && docker-compose logs --tail=50
echo "=== Disk Usage ===" && df -h
echo "=== Memory Usage ===" && free -h
```

---

## Version History

- **1.0** (2025-12-04) — Initial operational documentation for Power Strip architecture

---

**Last Updated**: December 4, 2025
**Status**: Active
**Next Review**: December 11, 2025
