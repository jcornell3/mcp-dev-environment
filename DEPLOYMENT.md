# Deployment Guide

This guide explains how to deploy MCP services to different hosting environments (local, VPS, etc.).

## Architecture

The repository contains environment-specific Docker Compose configurations:

- `docker-compose.yml.local` - Local WSL/development environment (ports 127.0.0.1:3004-3005)
- `docker-compose.yml.vps1` - VPS #1 at 5.78.159.29 (ports 0.0.0.0:3001-3003)

The active `docker-compose.yml` file is **not tracked in git** (it's in `.gitignore`) and must be created from the appropriate template for each environment.

## Local Deployment (WSL/Development)

Services: youtube-to-mp3, github

### Setup

1. Copy the local configuration:
   ```bash
   cp docker-compose.yml.local docker-compose.yml
   ```

2. Ensure `.env` file exists with local settings:
   ```bash
   MCP_ENV=development
   MCP_API_KEY=5b919081bcca34a32d8ac272e6691521cabbf71b1baace759cc6c710a3003c74
   DOWNLOADS_DIR=/mnt/c/Users/jcorn/Downloads
   GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here
   ```

3. Deploy:
   ```bash
   export MCP_API_KEY=5b919081bcca34a32d8ac272e6691521cabbf71b1baace759cc6c710a3003c74
   docker compose down
   docker compose up -d
   ```

4. Verify:
   ```bash
   curl -s http://127.0.0.1:3004/health
   curl -s http://127.0.0.1:3005/health
   ```

## VPS #1 Deployment (5.78.159.29)

Services: math, santa-clara, youtube-transcript

### Initial Setup

1. SSH to VPS:
   ```bash
   ssh root@5.78.159.29
   ```

2. Clone repository (if not already done):
   ```bash
   cd ~
   git clone <repository-url> mcp-dev-environment
   cd mcp-dev-environment
   ```

3. Copy the VPS configuration:
   ```bash
   cp docker-compose.yml.vps1 docker-compose.yml
   ```

4. Create `.env` file with VPS settings:
   ```bash
   cat > .env << 'EOF'
   MCP_ENV=production
   MCP_API_KEY=c64b03bb5b3cc7f8ab1582c7d3da229d7d57698790ca79c51d40d50510c6bb77
   DOMAIN=5.78.159.29
   HTTP_PORT=80
   HTTPS_PORT=443
   EOF
   ```

5. Configure firewall:
   ```bash
   ufw allow 22/tcp    # SSH
   ufw allow 3001/tcp  # Math service
   ufw allow 3002/tcp  # Santa Clara service
   ufw allow 3003/tcp  # YouTube Transcript service
   ufw --force enable
   ```

6. Deploy:
   ```bash
   docker compose down
   docker compose build
   docker compose up -d
   ```

7. Verify:
   ```bash
   curl -s http://localhost:3001/health
   curl -s http://localhost:3002/health
   curl -s http://localhost:3003/health
   ```

### Updating VPS Deployment

When pulling updates from git, the `docker-compose.yml` file will not be overwritten (it's gitignored).

1. SSH to VPS:
   ```bash
   ssh root@5.78.159.29
   cd ~/mcp-dev-environment
   ```

2. Pull latest code:
   ```bash
   git pull origin main
   ```

3. Rebuild services (use `--no-cache` if configuration changed):
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

4. Verify services:
   ```bash
   docker compose ps
   curl -s http://localhost:3001/health
   curl -s http://localhost:3002/health
   curl -s http://localhost:3003/health
   ```

### Troubleshooting

If you get merge conflicts on `docker-compose.yml` during `git pull`:

This shouldn't happen since `docker-compose.yml` is gitignored. If it does occur:

1. Check that `.gitignore` includes `docker-compose.yml`
2. Remove the file from git tracking:
   ```bash
   git rm --cached docker-compose.yml
   git commit -m "Remove docker-compose.yml from git tracking"
   ```
3. Recreate from template:
   ```bash
   cp docker-compose.yml.vps1 docker-compose.yml
   ```

## Claude Desktop Configuration

For hybrid deployment (both VPS and local services), configure Claude Desktop with dual bridges:

- VPS services (3001-3003): Use VPS_API_KEY `c64b03bb5b3cc7f8ab1582c7d3da229d7d57698790ca79c51d40d50510c6bb77`
- Local services (3004-3005): Use LOCAL_API_KEY `5b919081bcca34a32d8ac272e6691521cabbf71b1baace759cc6c710a3003c74`

See `claude_desktop_config.json` for complete configuration.

## Adding New VPS Environments

To add a second VPS:

1. Create `docker-compose.yml.vps2` with appropriate port mappings
2. Update this deployment guide with VPS #2 instructions
3. Follow the same deployment process as VPS #1
