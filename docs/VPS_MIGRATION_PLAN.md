# VPS Migration Plan: MCP Servers to 5.78.159.29

**Date**: December 6, 2025
**Target VPS**: 5.78.159.29
**Servers to Migrate**: math-mcp, santa-clara-mcp, youtube-transcript-mcp (+ optional: youtube-to-mp3, github-mcp)

---

## Executive Summary

The current MCP deployment is **already VPS-ready** with minimal configuration changes needed. All server code binds to `0.0.0.0` (accepts connections from any interface), uses environment variables for configuration, and includes health check endpoints.

**Only configuration files need updating** - no code changes required.

---

## Architecture Overview

### Current Setup (Local)
```
Claude Desktop (Windows)
    ↓ stdio via WSL
Universal Cloud Connector Bridge (WSL)
    server_url='http://127.0.0.1:3001/sse'
    ↓ HTTP/SSE
Docker Containers (Local)
    Ports: 127.0.0.1:3001-3005
```

### Target Setup (VPS Migration)
```
Claude Desktop (Windows)
    ↓ stdio via WSL
Universal Cloud Connector Bridge (WSL - stays local)
    server_url='http://5.78.159.29:3001/sse'
    ↓ HTTP/SSE over Internet
Docker Containers (VPS: 5.78.159.29)
    Ports: 0.0.0.0:3001-3005
```

**Key Decision**: Bridge stays local (WSL), only Docker containers move to VPS.

---

## Required Configuration Changes

### 1. Update VPS Code to Latest Version

**On VPS (5.78.159.29)**:
```bash
# Update mcp-dev-environment
cd ~/mcp-dev-environment
git pull origin main

# Verify latest commit (should be Dec 6, 2025)
git log -1
```

### 2. docker-compose.yml Port Bindings

**File**: `docker-compose.yml`

**Change** (apply to all 5 services):
```yaml
# BEFORE (localhost only)
ports:
  - "127.0.0.1:3001:3000"

# AFTER (all interfaces)
ports:
  - "0.0.0.0:3001:3000"
```

**Services to update**:
- math (port 3001)
- santa-clara (port 3002)
- youtube-transcript (port 3003)
- youtube-to-mp3 (port 3004)
- github-mcp (port 3005)

### 3. Environment Variables

**File**: `.env` (create on VPS)

```env
MCP_ENV=production
MCP_API_KEY=<generate-secure-token>
BRIDGE_API_TOKEN=<generate-another-token>
DOMAIN=5.78.159.29
HTTP_PORT=80
HTTPS_PORT=443
DOWNLOADS_DIR=/data/downloads
GITHUB_PERSONAL_ACCESS_TOKEN=<your-token>
```

**Generate secure tokens**:
```bash
openssl rand -hex 32
```

### 4. Volume Mounts (youtube-to-mp3)

**Create downloads directory on VPS**:
```bash
sudo mkdir -p /data/downloads
sudo chown -R $USER:$USER /data/downloads
```

### 5. Claude Desktop Config (Local Windows)

**File**: `C:\Users\jcorn\AppData\Roaming\Claude\claude_desktop_config.json`

**Update server_url for each bridge**:
```json
{
  "mcpServers": {
    "math-bridge": {
      "command": "wsl",
      "args": [
        "bash", "-c",
        "cd /home/jcornell/universal-cloud-connector && export server_url='http://5.78.159.29:3001/sse' && export api_token='<your-token>' && /home/jcornell/.nvm/versions/node/v24.11.1/bin/node dist/index.js"
      ]
    }
  }
}
```

**Changes**:
- `127.0.0.1` → `5.78.159.29`
- `default-api-key` → secure token (must match VPS `.env`)

---

## Migration Steps

### Step 1: Update VPS Code
```bash
ssh root@5.78.159.29
cd ~/mcp-dev-environment
git pull origin main
```

### Step 2: Configure VPS Environment
```bash
# Create .env file
nano .env
# Add configuration from section 3 above

# Create downloads directory
sudo mkdir -p /data/downloads
sudo chown -R $USER:$USER /data/downloads
```

### Step 3: Update docker-compose.yml
```bash
nano docker-compose.yml
# Change all port bindings from 127.0.0.1 to 0.0.0.0
```

### Step 4: Configure VPS Firewall
```bash
# Allow MCP server ports
sudo ufw allow 3001/tcp comment 'MCP math'
sudo ufw allow 3002/tcp comment 'MCP santa-clara'
sudo ufw allow 3003/tcp comment 'MCP youtube-transcript'

# Optional: for all 5 servers
sudo ufw allow 3004/tcp comment 'MCP youtube-to-mp3'
sudo ufw allow 3005/tcp comment 'MCP github'

# Enable and check
sudo ufw enable
sudo ufw status
```

### Step 5: Build and Start Services
```bash
docker-compose build
docker-compose up -d
docker-compose ps

# Check health
for port in 3001 3002 3003; do
  echo "Port $port:"
  curl -s http://localhost:$port/health
done
```

### Step 6: Test from VPS
```bash
# Test SSE connection
curl -H "Authorization: Bearer your-token" http://localhost:3001/sse
# Should see: event: endpoint, data: /messages?session_id=...
```

### Step 7: Update Local Bridge Config
```bash
# On Windows WSL
cd /mnt/c/Users/jcorn/AppData/Roaming/Claude
cp claude_desktop_config.json claude_desktop_config.json.backup
nano claude_desktop_config.json
# Update server_url and api_token
```

### Step 8: Test Bridge from Local
```bash
# On local WSL
cd /home/jcornell/universal-cloud-connector

echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
  server_url="http://5.78.159.29:3001/sse" \
  api_token="your-token" \
  node dist/index.js
```

### Step 9: Restart Claude Desktop
1. Close Claude Desktop completely
2. Reopen
3. Create new chat
4. Test: "What is 42 factorial?"

### Step 10: Verify All Services
- Math: "What is 123 + 456?"
- Santa Clara: "Look up property 288-13-033"
- YouTube: "Get transcript of <url>"

---

## Rollback Plan

```bash
# Restore local configuration
cd /mnt/c/Users/jcorn/AppData/Roaming/Claude
cp claude_desktop_config.json.backup claude_desktop_config.json

# Restart Claude Desktop
```

VPS services remain independent - no impact on local setup.

---

## Troubleshooting

### Connection Refused
- Check VPS firewall: `sudo ufw status`
- Check container: `docker-compose ps`
- Check logs: `docker-compose logs math`

### Invalid API Key (403)
- Verify tokens match: VPS `.env` vs local bridge config
- Regenerate and update both locations

### SSE Timeout
- Test connectivity: `ping 5.78.159.29`
- Test port: `telnet 5.78.159.29 3001`
- Test health: `curl http://5.78.159.29:3001/health`

---

## Success Criteria

- [ ] All containers running on VPS
- [ ] Health endpoints respond from VPS IP
- [ ] Local bridge connects to VPS
- [ ] Claude Desktop tools work
- [ ] No errors in logs

---

## Files Modified

### On VPS:
1. `docker-compose.yml` - Port bindings
2. `.env` - Environment variables
3. Firewall rules via `ufw`

### Locally:
1. `claude_desktop_config.json` - Bridge URLs and tokens

### No Code Changes:
- Server code already VPS-ready ✓
- Bridge code uses environment variables ✓
- Health checks implemented ✓

---

## Timeline Estimate

- VPS Configuration: 15 minutes
- Testing: 15 minutes
- Local Config: 5 minutes
- Verification: 10 minutes

**Total**: ~45 minutes

---

## Security Enhancements (Optional)

### Add HTTPS with Caddy
```bash
# Configure DNS first, then:
docker-compose up -d caddy
# Caddy auto-handles Let's Encrypt
```

### Restrict CORS
Update server files to allow only specific IPs instead of `*`

### Add Rate Limiting
Configure in Caddy or nginx reverse proxy

---

## Additional Notes

### Why This is Simple
- Architecture designed for HTTP/SSE transport
- No hardcoded IPs in code
- Bridge is transport-agnostic
- Servers already bind to 0.0.0.0

### Phased Migration
You can migrate servers one at a time:
1. Start with math (3001)
2. Then santa-clara (3002)
3. Then youtube-transcript (3003)
4. Later: youtube-to-mp3 (3004), github (3005)

Each server is independent - no dependencies.

---

## References

- [ARCHITECTURE.md](../../universal-cloud-connector/docs/ARCHITECTURE.md) - Bridge architecture
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Initial setup guide
- [Caddyfile](../Caddyfile) - Reverse proxy configuration (lines 63-115)
