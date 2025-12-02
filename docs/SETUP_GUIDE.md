# Setup Guide - Customizing for Your Environment

When you clone this project, several hardcoded paths and configurations are specific to the original developer's environment. This guide will help you customize them for your setup.

## Quick Setup Order

**For fastest setup, follow this order:**

1. Clone the repository
2. Start Docker services (`make start`) - this generates your container names
3. Check your container name (`docker compose ps`)
4. Update `claude_desktop_config.json` with your container name
5. Verify the config works
6. Test with Claude Desktop

## What Needs Changes vs. What Doesn't

**✓ Usually doesn't need changes:**
- Python code in `servers/santa-clara/` - works as-is
- `docker-compose.yml` service definition - auto-generates correct container names
- `Makefile` commands - work universally
- Documentation paths using `~/` - expand correctly on any system

**✗ Usually DOES need changes:**
- `claude_desktop_config.json` - container name must match your environment
- Windows Claude Desktop config file path - must use your Windows username
- `docs/README.md` line 29 - contains `USERNAME` placeholder (if you forked the repo)
- GitHub URLs in docs - if you forked to your own account

## Files to Update After Cloning

### 1. **claude_desktop_config.json** (Windows)
**Location:** `C:\Users\<YOUR-USERNAME>\AppData\Roaming\Claude\claude_desktop_config.json`

This file is NOT in the repository (for security). You need to create/update it based on your setup.

**Current Entry (jcornell3's setup):**
```json
{
  "mcpServers": {
    "santa-clara-local": {
      "command": "wsl",
      "args": [
        "docker",
        "exec",
        "-i",
        "mcp-dev-environment-santa-clara-1",
        "python",
        "-u",
        "/app/server.py"
      ]
    }
  }
}
```

**What to Change:**
- If your container name is different (check with `docker compose ps`), update `mcp-dev-environment-santa-clara-1` to your container name
- The `command`, `args`, and path `/app/server.py` should stay the same if you're using this project unchanged

**How to Find Your Container Name:**
```bash
# In WSL:
docker compose ps
# Look for: mcp-dev-environment-santa-clara-1 (or your custom name if changed)
```

---

### 2. **Update docs/README.md (Critical)**

**Location:** `docs/README.md` line 29

**Issue:** The Quick Start section contains a placeholder:
```bash
git clone git@github.com:USERNAME/mcp-dev-environment.git
```

**Fix:** Replace with your actual repository URL:

**If you're using the original repository:**
```bash
git clone git@github.com:jcornell3/mcp-dev-environment.git
```

**If you forked to your own GitHub account:**
```bash
git clone git@github.com:YOUR-USERNAME/mcp-dev-environment.git
```

This ensures users who read README.md from your repo get the correct clone URL.

### 3. **GitHub Repository URLs (Optional)**

If you forked this repository to your own account, update all GitHub references:

```bash
# Replace in all docs:
sed -i 's|github.com/jcornell3/mcp-dev-environment|github.com/YOUR-USERNAME/mcp-dev-environment|g' docs/*.md
```

**Files that contain GitHub references:**
- `docs/README.md` - Clone URL and repository links
- `docs/DOCUMENTATION_INDEX.md` - Links to documentation
- `docs/MCP_DEV_ENVIRONMENT_SUMMARY.md` - Repository URL
- `docs/CLAUDE.md` - Repository URL

### 4. **Documentation Path References (Usually Safe)**

Most documentation files use `~/` for home directory paths, which expand correctly on any system. However, review these files to ensure they match your setup:

**Files to review:**
- `docs/FRESH_WORKSTATION_SETUP.md` - Contains setup examples
- `docs/MCP_DEVELOPMENT_LESSONS_LEARNED.md` - References to file paths
- `docs/WRAPPER_SETUP.md` - Configuration examples (deprecated, HTTP-based approach)

These should work universally with `~/`, but if you see `/home/jcornell/`, replace with your actual home path.

---

### 5. **Docker Container Name (If Customized)**

By default, Docker auto-generates the container name as `mcp-dev-environment-santa-clara-1` based on your project directory.

**Only modify this section if you:**
- Renamed the `santa-clara` service in `docker-compose.yml`, OR
- Changed your project directory name

If you did modify the service name:

1. Run `docker compose ps` to find your actual container name
2. Update the container name in `claude_desktop_config.json`
3. Update any MCP JSON-RPC test commands in documentation

### 6. **MCP Server Configuration** (Advanced - If Modifying)
If you modify `servers/santa-clara/` or add new servers:

**Update `claude_desktop_config.json` to register your server:**
```json
{
  "mcpServers": {
    "your-server-name": {
      "command": "wsl",
      "args": [
        "docker",
        "exec",
        "-i",
        "your-container-name",
        "python",
        "-u",
        "/app/server.py"
      ]
    }
  }
}
```

---

## Platform-Specific Setup

### Windows + WSL + VS Code

This is the primary supported platform. Follow the standard setup above.

**Key Points:**
- Claude Desktop config goes in Windows AppData: `C:\Users\<YOUR-USERNAME>\AppData\Roaming\Claude\claude_desktop_config.json`
- Run `docker` and `make` commands in WSL terminal
- Claude Desktop connects via `wsl docker exec` (already configured)

### macOS

Claude Desktop configuration differs on macOS:

**Config location:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Note:** The stdio-based MCP server uses `docker exec`, which requires Docker Desktop. The `wsl` command won't work on native macOS - use `docker` directly instead:

```json
{
  "mcpServers": {
    "santa-clara-local": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "mcp-dev-environment-santa-clara-1",
        "python",
        "-u",
        "/app/server.py"
      ]
    }
  }
}
```

### Linux (Native)

**Config location:**
```
~/.config/Claude/claude_desktop_config.json
```

**Command:** Same as macOS - use `docker` directly:

```json
{
  "mcpServers": {
    "santa-clara-local": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "mcp-dev-environment-santa-clara-1",
        "python",
        "-u",
        "/app/server.py"
      ]
    }
  }
}
```

## Environment-Specific Items

### Home Directory Paths
- `~/mcp-dev-environment` - Home directory path (works as-is on any system)
- Expands to `/home/username` on Linux, `/Users/username` on macOS, `C:\Users\username` on Windows WSL

### Container Names
- `mcp-dev-environment-santa-clara-1` - Default from docker-compose.yml (matches your project directory name)
- Verify with: `docker compose ps`
- Can be customized in `docker-compose.yml` if needed

### GitHub Repository
- `https://github.com/jcornell3/mcp-dev-environment` - Original repository
- If you forked this, update documentation URLs to point to your fork
- Original can be used as upstream to pull future updates

---

## Verification Steps (Before Restarting Claude Desktop)

**Before restarting Claude Desktop, verify your config is correct:**

### 1. Container is Running
```bash
docker compose ps
```
**Expected output:** One line showing `mcp-dev-environment-santa-clara-1` with status `Up`

### 2. Get Exact Container Name
```bash
# Copy the exact name from the CONTAINER_ID column
docker compose ps
```

### 3. Verify MCP Server Responds
```bash
# Test the server directly (inside the container)
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | docker exec -i mcp-dev-environment-santa-clara-1 python -u /app/server.py
```

**Expected output:** JSON response with server capabilities, no errors

### 4. Verify Config File Exists and is Valid
```bash
# Windows PowerShell
cat "$env:APPDATA\Claude\claude_desktop_config.json"

# macOS/Linux
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
# or
cat ~/.config/Claude/claude_desktop_config.json
```

**Expected output:** Valid JSON with `mcp-dev-environment-santa-clara-1` (or your custom container name)

If these steps pass, Claude Desktop should connect successfully.

---

## Quick Checklist

After cloning and before testing with Claude Desktop:

- [ ] **Run Initial Setup**
  - Clone: `git clone https://github.com/jcornell3/mcp-dev-environment.git`
  - Start: `make start` (or `docker compose up -d`)
  - Wait: ~10 seconds for container to fully start

- [ ] **Check Container Name**
  - Run: `docker compose ps`
  - Copy exact container name (usually `mcp-dev-environment-santa-clara-1`)

- [ ] **Update Claude Desktop Config**
  - Create/edit config at platform-specific location (see Platform-Specific Setup section)
  - Update container name to match `docker compose ps` output
  - Ensure it's valid JSON (no trailing commas)

- [ ] **Verify Config**
  - Run verification steps above
  - Test initialize command works without errors

- [ ] **Update docs/README.md** (if needed)
  - Line 29: Replace `USERNAME` with your GitHub username (if forked)
  - Otherwise, keep as `jcornell3`

- [ ] **Update GitHub URLs** (if forked)
  - Use provided sed command to replace `jcornell3` with your username
  - Or manually update URLs in documentation files

- [ ] **Restart Claude Desktop**
  - Completely quit Claude Desktop (not just minimize)
  - Relaunch Claude Desktop
  - Test that tools are available

---

## Common Issues

**"Container not found" error:**
- Check container name: `docker compose ps`
- Update container name in `claude_desktop_config.json`

**Claude Desktop not connecting:**
- Verify `claude_desktop_config.json` is in correct Windows path
- Verify container is running: `docker compose ps` shows `Up`
- Restart Claude Desktop completely after config changes

**Path errors in documentation:**
- Most paths use `~/` which expands to your home directory
- If seeing `/home/jcornell/`, replace with your actual home path

---

## Need Help?

Refer to:
1. `docs/FRESH_WORKSTATION_SETUP.md` - Complete setup guide
2. `docs/MCP_DEVELOPMENT_LESSONS_LEARNED.md` - Troubleshooting
3. README.md - Quick start and overview
