# VPS Migration Plan: Hybrid Deployment (3 VPS + 2 Local)

**Date**: December 6, 2025
**Target VPS**: 5.78.159.29
**Deployment Model**: Hybrid - Split between VPS and local

**VPS Services** (Remote):
- math-mcp (port 3001)
- santa-clara-mcp (port 3002)
- youtube-transcript-mcp (port 3003)

**Local Services** (Stay on WSL):
- youtube-to-mp3-mcp (port 3004) - Requires local file system access
- github-mcp (port 3005) - Uses local GitHub token

---

## Executive Summary

This is a **hybrid deployment** where 3 production services move to VPS while 2 remain local. Claude Desktop will use **two separate Universal Cloud Connector instances**:
1. **VPS Bridge** - Connects to remote services (math, santa-clara, youtube-transcript)
2. **Local Bridge** - Connects to local services (youtube-to-mp3, github)

**Only configuration files need updating** - no code changes required.

---

## Architecture Overview

### Current Setup (All Local)
```
Claude Desktop (Windows)
    ↓ stdio via WSL
Universal Cloud Connector Bridge (WSL)
    ↓ HTTP/SSE
Docker Containers (Local WSL)
    ├── math-mcp (127.0.0.1:3001)
    ├── santa-clara-mcp (127.0.0.1:3002)
    ├── youtube-transcript-mcp (127.0.0.1:3003)
    ├── youtube-to-mp3-mcp (127.0.0.1:3004)
    └── github-mcp (127.0.0.1:3005)
```

### Target Setup (Hybrid Deployment)
```
Claude Desktop (Windows)
    ↓ stdio via WSL
    ├─ VPS Bridge Instance (for remote services)
    │   ↓ HTTP/SSE over Internet
    │   VPS Docker Containers (5.78.159.29)
    │       ├── math-mcp (0.0.0.0:3001)
    │       ├── santa-clara-mcp (0.0.0.0:3002)
    │       └── youtube-transcript-mcp (0.0.0.0:3003)
    │
    └─ Local Bridge Instance (for local services)
        ↓ HTTP/SSE localhost
        Local Docker Containers (WSL)
            ├── youtube-to-mp3-mcp (127.0.0.1:3004)
            └── github-mcp (127.0.0.1:3005)
```

**Key Architecture Decision**:
- **Two Universal Cloud Connector instances** in Claude Desktop config
- **VPS Bridge** connects to remote services (math, santa-clara, youtube-transcript)
- **Local Bridge** connects to local services (youtube-to-mp3, github)
- Each bridge instance is independent with its own server_url

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

#### On VPS (5.78.159.29)

**File**: `~/mcp-dev-environment/docker-compose.yml`

**Change** (apply to VPS services only):
```yaml
# BEFORE (localhost only)
ports:
  - "127.0.0.1:3001:3000"

# AFTER (all interfaces - VPS only)
ports:
  - "0.0.0.0:3001:3000"
```

**VPS Services to update**:
- math (port 3001) → `0.0.0.0:3001:3000`
- santa-clara (port 3002) → `0.0.0.0:3002:3000`
- youtube-transcript (port 3003) → `0.0.0.0:3003:3000`

**Remove from VPS docker-compose.yml**:
- youtube-to-mp3 service (stays local)
- github-mcp service (stays local)

#### On Local WSL

**File**: `/home/jcornell/mcp-dev-environment/docker-compose.yml`

**Keep localhost binding** (no changes):
```yaml
# Local services stay on 127.0.0.1
youtube-to-mp3:
  ports:
    - "127.0.0.1:3004:3000"

github-mcp:
  ports:
    - "127.0.0.1:3005:3000"
```

**Remove from local docker-compose.yml after migration**:
- math service (moved to VPS)
- santa-clara service (moved to VPS)
- youtube-transcript service (moved to VPS)

### 3. Environment Variables & API Tokens

⚠️ **SECURITY CRITICAL:** Never use `default-api-key` in production!

**Generate secure API tokens** (run these commands):
```bash
# Generate VPS_API_KEY (for VPS services: math, santa-clara, youtube-transcript)
openssl rand -hex 32

# Generate LOCAL_API_KEY (for local services: youtube-to-mp3, github)
openssl rand -hex 32

# Save both tokens - you'll need them in Claude Desktop config
```

#### VPS Environment (.env on VPS)

**File**: `~/mcp-dev-environment/.env` (on VPS 5.78.159.29)

```env
MCP_ENV=production

# VPS API KEY - Use the VPS_API_KEY generated above
MCP_API_KEY=<paste-VPS-token-here>

# Domain Configuration
DOMAIN=5.78.159.29
HTTP_PORT=80
HTTPS_PORT=443
```

**Note**: VPS does NOT need:
- `DOWNLOADS_DIR` (youtube-to-mp3 is local)
- `GITHUB_PERSONAL_ACCESS_TOKEN` (github-mcp is local)

#### Local Environment (.env on WSL)

**File**: `/home/jcornell/mcp-dev-environment/.env` (on local WSL)

```env
MCP_ENV=development

# Local API KEY - Use the LOCAL_API_KEY generated above
MCP_API_KEY=<paste-LOCAL-token-here>

# Storage for youtube-to-mp3
DOWNLOADS_DIR=/home/jcornell/downloads

# GitHub Token for github-mcp server
GITHUB_PERSONAL_ACCESS_TOKEN=<your-existing-github-token>
```

#### Token Usage Summary

| Service | Location | API Key | Used In |
|---------|----------|---------|---------|
| math-mcp | VPS | VPS_API_KEY | VPS bridge config |
| santa-clara-mcp | VPS | VPS_API_KEY | VPS bridge config |
| youtube-transcript-mcp | VPS | VPS_API_KEY | VPS bridge config |
| youtube-to-mp3-mcp | Local | LOCAL_API_KEY | Local bridge config |
| github-mcp | Local | LOCAL_API_KEY | Local bridge config |

### 4. Claude Desktop Config - Dual Bridge Configuration

**File**: `C:\Users\jcorn\AppData\Roaming\Claude\claude_desktop_config.json`

This config requires **TWO sets of bridges** - one pointing to VPS, one pointing to local:

```json
{
  "mcpServers": {
    "// VPS BRIDGES - Remote Services": "",

    "math-vps": {
      "command": "wsl",
      "args": [
        "bash", "-c",
        "cd /home/jcornell/universal-cloud-connector && export server_url='http://5.78.159.29:3001/sse' && export api_token='<VPS_API_KEY>' && /home/jcornell/.nvm/versions/node/v24.11.1/bin/node dist/index.js"
      ]
    },

    "santa-clara-vps": {
      "command": "wsl",
      "args": [
        "bash", "-c",
        "cd /home/jcornell/universal-cloud-connector && export server_url='http://5.78.159.29:3002/sse' && export api_token='<VPS_API_KEY>' && /home/jcornell/.nvm/versions/node/v24.11.1/bin/node dist/index.js"
      ]
    },

    "youtube-transcript-vps": {
      "command": "wsl",
      "args": [
        "bash", "-c",
        "cd /home/jcornell/universal-cloud-connector && export server_url='http://5.78.159.29:3003/sse' && export api_token='<VPS_API_KEY>' && /home/jcornell/.nvm/versions/node/v24.11.1/bin/node dist/index.js"
      ]
    },

    "// LOCAL BRIDGES - Local Services": "",

    "youtube-to-mp3-local": {
      "command": "wsl",
      "args": [
        "bash", "-c",
        "cd /home/jcornell/universal-cloud-connector && export server_url='http://127.0.0.1:3004/sse' && export api_token='<LOCAL_API_KEY>' && /home/jcornell/.nvm/versions/node/v24.11.1/bin/node dist/index.js"
      ]
    },

    "github-local": {
      "command": "wsl",
      "args": [
        "bash", "-c",
        "cd /home/jcornell/universal-cloud-connector && export server_url='http://127.0.0.1:3005/sse' && export api_token='<LOCAL_API_KEY>' && /home/jcornell/.nvm/versions/node/v24.11.1/bin/node dist/index.js"
      ]
    }
  }
}
```

**Configuration Summary**:

| Bridge Name | Server URL | API Token | Connects To |
|-------------|------------|-----------|-------------|
| math-vps | http://5.78.159.29:3001/sse | VPS_API_KEY | VPS math service |
| santa-clara-vps | http://5.78.159.29:3002/sse | VPS_API_KEY | VPS santa-clara service |
| youtube-transcript-vps | http://5.78.159.29:3003/sse | VPS_API_KEY | VPS youtube-transcript service |
| youtube-to-mp3-local | http://127.0.0.1:3004/sse | LOCAL_API_KEY | Local youtube-to-mp3 service |
| github-local | http://127.0.0.1:3005/sse | LOCAL_API_KEY | Local github service |

**Key Points**:
- Each bridge is a separate Universal Cloud Connector instance
- VPS bridges use VPS IP and VPS_API_KEY
- Local bridges use 127.0.0.1 and LOCAL_API_KEY
- All run concurrently in Claude Desktop

---

## Migration Steps

### Phase A: VPS Deployment (3 Services)

#### Step 1: Update VPS Code
```bash
ssh root@5.78.159.29
cd ~/mcp-dev-environment
git pull origin main
```

#### Step 2: Configure VPS Environment
```bash
# Generate VPS API key
openssl rand -hex 32
# Save this as VPS_API_KEY

# Create .env file on VPS
nano .env
```

Add VPS configuration:
```env
MCP_ENV=production
MCP_API_KEY=<paste-VPS_API_KEY-here>
DOMAIN=5.78.159.29
HTTP_PORT=80
HTTPS_PORT=443
```

#### Step 3: Create VPS-only docker-compose.yml

**On VPS**, create a docker-compose.yml with **ONLY the 3 VPS services**:

```bash
nano docker-compose.yml
```

**VPS docker-compose.yml** (only math, santa-clara, youtube-transcript):
```yaml
version: '3.8'

services:
  math:
    build: ./servers/math-mcp
    container_name: mcp-math
    ports:
      - "0.0.0.0:3001:3000"  # VPS: bind to all interfaces
    environment:
      - PORT=3000
      - MCP_API_KEY=${MCP_API_KEY}
    restart: unless-stopped

  santa-clara:
    build: ./servers/santa-clara
    container_name: mcp-santa-clara
    ports:
      - "0.0.0.0:3002:3000"  # VPS: bind to all interfaces
    environment:
      - PORT=3000
      - MCP_API_KEY=${MCP_API_KEY}
    restart: unless-stopped

  youtube-transcript:
    build: ./servers/youtube-transcript-mcp
    container_name: mcp-youtube-transcript
    ports:
      - "0.0.0.0:3003:3000"  # VPS: bind to all interfaces
    environment:
      - PORT=3000
      - MCP_API_KEY=${MCP_API_KEY}
    restart: unless-stopped
```

#### Step 4: Configure VPS Firewall (3 ports only)
```bash
# Allow ONLY the 3 VPS service ports
sudo ufw allow 3001/tcp comment 'MCP math'
sudo ufw allow 3002/tcp comment 'MCP santa-clara'
sudo ufw allow 3003/tcp comment 'MCP youtube-transcript'

# Enable and check
sudo ufw enable
sudo ufw status
```

#### Step 5: Build and Start VPS Services (3 services)
```bash
# Build only the 3 VPS services
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# Check health (3 services)
for port in 3001 3002 3003; do
  echo "Port $port:"
  curl -s http://localhost:$port/health
done
```

### Phase B: Local Services Configuration (2 Services)

#### Step 6: Configure Local Environment

**On local WSL** (`/home/jcornell/mcp-dev-environment`):

```bash
# Generate LOCAL API key
openssl rand -hex 32
# Save this as LOCAL_API_KEY

# Create/update .env file
nano .env
```

Add local configuration:
```env
MCP_ENV=development
MCP_API_KEY=<paste-LOCAL_API_KEY-here>
DOWNLOADS_DIR=/home/jcornell/downloads
GITHUB_PERSONAL_ACCESS_TOKEN=<your-existing-github-token>
```

#### Step 7: Create Local-only docker-compose.yml

**On local WSL**, update docker-compose.yml with **ONLY the 2 local services**:

```bash
cd /home/jcornell/mcp-dev-environment
nano docker-compose.yml
```

**Local docker-compose.yml** (only youtube-to-mp3, github):
```yaml
version: '3.8'

services:
  youtube-to-mp3:
    build: ./servers/youtube-to-mp3-mcp
    container_name: mcp-youtube-to-mp3
    ports:
      - "127.0.0.1:3004:3000"  # Local: localhost only
    environment:
      - PORT=3000
      - MCP_API_KEY=${MCP_API_KEY}
      - DOWNLOADS_DIR=${DOWNLOADS_DIR}
    volumes:
      - ${DOWNLOADS_DIR}:/downloads
    restart: unless-stopped

  github-mcp:
    build: ./servers/shared/github-mcp-http-wrapper
    container_name: mcp-github
    ports:
      - "127.0.0.1:3005:3000"  # Local: localhost only
    environment:
      - PORT=3000
      - MCP_API_KEY=${MCP_API_KEY}
      - GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PERSONAL_ACCESS_TOKEN}
    restart: unless-stopped
```

#### Step 8: Restart Local Services (2 services)
```bash
# Rebuild and restart local services
docker-compose build
docker-compose down
docker-compose up -d

# Check health (2 services)
for port in 3004 3005; do
  echo "Port $port:"
  curl -s http://localhost:$port/health
done
```

### Phase C: Testing and Validation

#### Step 9: Test VPS Services from VPS

**On VPS**, test the 3 remote services:

```bash
# Test SSE connections from VPS
for port in 3001 3002 3003; do
  echo "Testing port $port:"
  curl -H "Authorization: Bearer <VPS_API_KEY>" http://localhost:$port/sse
  echo ""
done
# Each should return: event: endpoint, data: /messages?session_id=...
```

#### Step 10: Update Claude Desktop Config

**On Windows**, backup and update Claude Desktop config:

```bash
# Via WSL
cd /mnt/c/Users/jcorn/AppData/Roaming/Claude
cp claude_desktop_config.json claude_desktop_config.json.backup
```

Update `claude_desktop_config.json` with the dual bridge configuration from Section 4 above.

**Replace placeholders**:
- `<VPS_API_KEY>` → Your generated VPS API key
- `<LOCAL_API_KEY>` → Your generated LOCAL API key

#### Step 11: Test Bridges from Local WSL

**Test VPS bridges**:
```bash
cd /home/jcornell/universal-cloud-connector

# Test math VPS bridge
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
  server_url="http://5.78.159.29:3001/sse" \
  api_token="<VPS_API_KEY>" \
  node dist/index.js

# Test santa-clara VPS bridge
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
  server_url="http://5.78.159.29:3002/sse" \
  api_token="<VPS_API_KEY>" \
  node dist/index.js
```

**Test local bridges**:
```bash
# Test youtube-to-mp3 local bridge
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
  server_url="http://127.0.0.1:3004/sse" \
  api_token="<LOCAL_API_KEY>" \
  node dist/index.js

# Test github local bridge
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
  server_url="http://127.0.0.1:3005/sse" \
  api_token="<LOCAL_API_KEY>" \
  node dist/index.js
```

#### Step 12: Restart Claude Desktop and Verify

1. **Close Claude Desktop completely**
2. **Reopen Claude Desktop**
3. **Create new chat**
4. **Test each service**:

**VPS Services**:
- Math: "What is 42 factorial?"
- Santa Clara: "Look up property 288-13-033"
- YouTube Transcript: "Get transcript of https://youtube.com/watch?v=dQw4w9WgXcQ"

**Local Services**:
- YouTube to MP3: "Convert https://youtube.com/watch?v=... to MP3"
- GitHub: "Search for Python repos with 50k+ stars"

#### Step 13: Verify Hybrid Deployment

**Expected behavior**:
- ✅ VPS services respond from 5.78.159.29
- ✅ Local services respond from localhost
- ✅ All 5 services available in Claude Desktop
- ✅ No errors in Claude Desktop logs (Help → Export Logs)

---

## VPS Security

### Port Binding Strategy

**Local Development (Current)**:
```yaml
ports:
  - "127.0.0.1:3001:3000"  # Secure: localhost only
```
Protects from local network access - services only accessible from same machine.

**VPS Deployment (This Migration)**:
```yaml
ports:
  - "0.0.0.0:3001:3000"  # Required: external access needed
```
Binds to all interfaces - **required** for remote access from your Windows machine.

### Security Layers (VPS Only)

**1. Firewall (ufw)**
- **VPS**: Only ports 3001-3003 exposed (for MCP services)
- Optional: Restrict ports 3001-3003 to your IP only
- **Local**: No firewall changes needed (localhost-only binding)

**2. Bearer Token Authentication**
- **VPS services**: Use VPS_API_KEY (32-byte hex)
- **Local services**: Use LOCAL_API_KEY (32-byte hex)
- All requests require `Authorization: Bearer <token>` header
- Tokens never logged or stored in databases

**3. HTTPS with Caddy (Optional)**
- Can be added later for VPS services
- Automatic Let's Encrypt certificates
- HTTPS encryption for all traffic
- Not required for initial deployment (Bearer auth sufficient)

**4. Network Isolation**
- **VPS**: Services bind to `0.0.0.0` (required for remote access)
- **Local**: Services bind to `127.0.0.1` (localhost-only, no external access)
- Different API keys for VPS vs local prevent unauthorized cross-access

### VPS Security Checklist

Before going live, verify:

- [ ] Firewall configured on VPS (`sudo ufw status`)
- [ ] Only ports 3001-3003 exposed on VPS (not 3004-3005)
- [ ] Strong VPS_API_KEY generated (not `default-api-key`)
- [ ] Strong LOCAL_API_KEY generated (different from VPS key)
- [ ] VPS `.env` file has restrictive permissions (`chmod 600 .env`)
- [ ] Local `.env` file has restrictive permissions (`chmod 600 .env`)
- [ ] No GitHub token in VPS `.env` (only in local `.env`)
- [ ] No `DOWNLOADS_DIR` in VPS `.env` (only in local `.env`)
- [ ] Regular security updates scheduled on VPS (`apt update && apt upgrade`)
- [ ] Docker socket access restricted (only sudoers)

### Hybrid Network Diagram

```
Internet
    ↓
Firewall (ufw) - VPS only allows 3001-3003
    ↓
VPS Docker Network (5.78.159.29)
  ├─ math-mcp:3001 (0.0.0.0:3001, Bearer: VPS_API_KEY)
  ├─ santa-clara-mcp:3002 (0.0.0.0:3002, Bearer: VPS_API_KEY)
  └─ youtube-transcript-mcp:3003 (0.0.0.0:3003, Bearer: VPS_API_KEY)

Local WSL Docker Network (127.0.0.1)
  ├─ youtube-to-mp3-mcp:3004 (127.0.0.1:3004, Bearer: LOCAL_API_KEY)
  └─ github-mcp:3005 (127.0.0.1:3005, Bearer: LOCAL_API_KEY)

Claude Desktop (Windows)
    ↓
Universal Cloud Connector Bridges (WSL)
  ├─ 3 VPS bridges → 5.78.159.29:3001-3003 (with VPS_API_KEY)
  └─ 2 Local bridges → 127.0.0.1:3004-3005 (with LOCAL_API_KEY)
```

**Security Properties**:
- VPS services accessible from internet (firewall + bearer auth protection)
- Local services only accessible from same machine (localhost binding)
- Different API keys prevent unauthorized cross-access
- No sensitive data (GitHub token, downloads) leaves local machine

---

## Rollback Plan

### Rollback VPS Services (Return to All-Local)

If you need to rollback and run all 5 services locally again:

**Step 1: Restore Local docker-compose.yml**

Add back the 3 VPS services to local docker-compose.yml:

```bash
cd /home/jcornell/mcp-dev-environment
```

Update `docker-compose.yml` to include all 5 services with localhost binding:
```yaml
services:
  math:
    ports:
      - "127.0.0.1:3001:3000"  # Localhost only

  santa-clara:
    ports:
      - "127.0.0.1:3002:3000"  # Localhost only

  youtube-transcript:
    ports:
      - "127.0.0.1:3003:3000"  # Localhost only

  youtube-to-mp3:
    ports:
      - "127.0.0.1:3004:3000"  # Localhost only

  github-mcp:
    ports:
      - "127.0.0.1:3005:3000"  # Localhost only
```

**Step 2: Restart Local Services**

```bash
docker-compose build
docker-compose up -d
```

**Step 3: Restore Claude Desktop Config**

```bash
cd /mnt/c/Users/jcorn/AppData/Roaming/Claude
cp claude_desktop_config.json.backup claude_desktop_config.json
```

**Step 4: Restart Claude Desktop**

All services now running locally again. VPS services can remain running independently.

---

## Troubleshooting

### VPS Service Issues

**Connection Refused to VPS**
- Check VPS firewall: `sudo ufw status`
- Verify ports 3001-3003 allowed
- Check container on VPS: `docker-compose ps`
- Check logs on VPS: `docker-compose logs math`

**Invalid API Key (403) - VPS Services**
- Verify VPS_API_KEY matches in:
  1. VPS `.env` file
  2. Claude Desktop config VPS bridge `api_token`
- Regenerate VPS_API_KEY and update both locations

**SSE Timeout - VPS**
- Test connectivity: `ping 5.78.159.29`
- Test port: `telnet 5.78.159.29 3001`
- Test health: `curl http://5.78.159.29:3001/health`
- Check VPS firewall isn't blocking your IP

### Local Service Issues

**Connection Refused to Local**
- Check containers running: `docker-compose ps`
- Check logs: `docker-compose logs github-mcp`
- Verify ports 3004-3005 not blocked locally

**Invalid API Key (403) - Local Services**
- Verify LOCAL_API_KEY matches in:
  1. Local `.env` file
  2. Claude Desktop config local bridge `api_token`
- Regenerate LOCAL_API_KEY and update both locations

**GitHub MCP "No Token" Error**
- Verify `GITHUB_PERSONAL_ACCESS_TOKEN` in local `.env`
- Check token hasn't expired
- Rebuild github-mcp container after adding token

### Claude Desktop Issues

**Tools Not Appearing**
- Verify all 5 bridge configs in `claude_desktop_config.json`
- Completely close and restart Claude Desktop
- Create new chat session
- Check Claude Desktop logs (Help → Export Logs)

**Mixed VPS/Local Not Working**
- Ensure VPS bridges use VPS_API_KEY
- Ensure local bridges use LOCAL_API_KEY
- Verify VPS services use port 3001-3003
- Verify local services use port 3004-3005

---

## Success Criteria

**VPS Services** (3 services):
- [ ] Math, santa-clara, youtube-transcript running on VPS
- [ ] Health endpoints respond from 5.78.159.29:3001-3003
- [ ] VPS bridges connect successfully
- [ ] VPS tools work in Claude Desktop

**Local Services** (2 services):
- [ ] Youtube-to-mp3, github running locally
- [ ] Health endpoints respond from 127.0.0.1:3004-3005
- [ ] Local bridges connect successfully
- [ ] Local tools work in Claude Desktop

**Overall**:
- [ ] All 5 tools available in Claude Desktop
- [ ] No errors in Claude Desktop logs
- [ ] VPS and local services independent

---

## Files Modified

### On VPS (5.78.159.29):
1. `docker-compose.yml` - **Only 3 services** (math, santa-clara, youtube-transcript)
2. `.env` - VPS environment with VPS_API_KEY
3. Firewall rules - **Only ports 3001-3003** allowed

### On Local WSL (/home/jcornell/mcp-dev-environment):
1. `docker-compose.yml` - **Only 2 services** (youtube-to-mp3, github)
2. `.env` - Local environment with LOCAL_API_KEY and GitHub token

### On Windows (Claude Desktop):
1. `claude_desktop_config.json` - **5 bridge instances** (3 VPS + 2 local)

### No Code Changes:
- Server code already VPS-ready ✓
- Bridge code uses environment variables ✓
- Health checks implemented ✓
- Services are location-agnostic ✓

---

## Timeline Estimate

**Phase A: VPS Deployment**
- VPS Configuration: 15 minutes
- VPS Service Build: 10 minutes
- VPS Testing: 10 minutes

**Phase B: Local Reconfiguration**
- Local docker-compose update: 5 minutes
- Local Service Rebuild: 5 minutes
- Local Testing: 5 minutes

**Phase C: Integration**
- Claude Desktop Config: 10 minutes
- End-to-End Testing: 15 minutes
- Verification: 10 minutes

**Total**: ~85 minutes (1.5 hours)

---

## Deployment Summary

### What Moves to VPS
✅ **3 Services**:
- math-mcp (general computation, no local dependencies)
- santa-clara-mcp (static property data, no local dependencies)
- youtube-transcript-mcp (API-based, no local dependencies)

### What Stays Local
✅ **2 Services**:
- youtube-to-mp3-mcp (requires local file system for downloads)
- github-mcp (uses local GitHub token, security preference)

### Why Hybrid Makes Sense
- **Performance**: Stateless services on VPS, file-heavy services local
- **Security**: GitHub token never leaves local machine
- **Flexibility**: Local downloads directory under your control
- **Scalability**: Can move more services to VPS later if needed
- **Cost**: Only pay for VPS resources you need

---

## Future Enhancements (Post-Migration)

### Add HTTPS with Caddy (VPS)
```bash
# After DNS configured to point to 5.78.159.29
docker-compose up -d caddy
# Caddy auto-handles Let's Encrypt
```

### Move More Services to VPS
If you later want to move youtube-to-mp3 or github to VPS:
1. Add services to VPS docker-compose.yml
2. Update VPS .env with needed variables
3. Update Claude Desktop config to point to VPS
4. Remove from local docker-compose.yml

### Add Monitoring (VPS)
- Prometheus + Grafana for metrics
- Uptime monitoring
- Log aggregation

---

## References

- [ARCHITECTURE.md](../../universal-cloud-connector/docs/ARCHITECTURE.md) - Bridge architecture
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Initial setup guide
- [Caddyfile](../Caddyfile) - Reverse proxy configuration (lines 63-115)
