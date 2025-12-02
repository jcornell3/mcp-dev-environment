# Setup Guide - Customizing for Your Environment

When you clone this project, several hardcoded paths and configurations are specific to the original developer's environment. This guide will help you customize them for your setup.

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

### 2. **Documentation References**
Several documentation files contain references to the original repository and file paths.

**Search and Replace Examples:**

If you forked this repository to your own GitHub account:
```bash
# Replace in all docs:
sed -i 's|github.com/jcornell3/mcp-dev-environment|github.com/YOUR-USERNAME/mcp-dev-environment|g' docs/*.md
```

**Files that may reference paths:**
- `docs/FRESH_WORKSTATION_SETUP.md` - Contains setup examples
- `docs/MCP_DEVELOPMENT_LESSONS_LEARNED.md` - References to file paths
- `docs/WRAPPER_SETUP.md` - Configuration examples

These use `~/` for home directory, which should work universally, but review them to ensure they match your environment.

---

### 3. **Docker Container Name**
If you renamed the `santa-clara` service in `docker-compose.yml`:

1. Update the container name in all MCP JSON-RPC test commands
2. Update `claude_desktop_config.json` (see #1 above)
3. Update any documentation that references the container name

---

### 4. **MCP Server Configuration** (if modifying)
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

## Environment-Specific Items

### WSL/Windows Paths
- `~/mcp-dev-environment` - Home directory path (should work as-is on any system)
- `C:\Users\jcorn\AppData\Roaming\Claude\` - **REPLACE** `jcorn` with your Windows username

### Container Names
- `mcp-dev-environment-santa-clara-1` - Default from docker-compose.yml (matches your project directory name)
- Can be customized in `docker-compose.yml` if needed

### GitHub Repository
- `https://github.com/jcornell3/mcp-dev-environment` - If you forked this, update to your fork
- Original can be used as upstream for updates

---

## Quick Checklist

After cloning, verify/update:

- [ ] **Windows Claude Desktop Config**
  - Location: `C:\Users\<YOUR-USERNAME>\AppData\Roaming\Claude\claude_desktop_config.json`
  - Verify container name matches `docker compose ps` output

- [ ] **Docker Container**
  - Run: `docker compose ps`
  - Confirm container name matches config

- [ ] **GitHub URL** (if forked)
  - Update in documentation if you want to point to your fork
  - Or keep original to sync updates

- [ ] **Test the Setup**
  - Start services: `docker compose up -d`
  - Test initialize: See Quick Start in README.md

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
