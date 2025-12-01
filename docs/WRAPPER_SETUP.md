# Santa Clara MCP Wrapper Setup

This document describes how to configure Claude Desktop to use the santa-clara MCP server via a stdio wrapper.

## Overview

The santa-clara MCP server runs as an HTTP service behind an Nginx reverse proxy at `https://localhost:8443/santa-clara/mcp`. To integrate it with Claude Desktop (which expects stdio-based MCP connections), we use a wrapper script that bridges HTTP requests to stdin/stdout.

## Files Created

### 1. Wrapper Script
**Location:** `scripts/santa-clara-wrapper.sh`

A bash script that:
- Reads JSON-RPC 2.0 requests from stdin
- Forwards them to the HTTP endpoint via `curl`
- Returns responses on stdout

**Test the wrapper directly:**
```bash
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
  ./scripts/santa-clara-wrapper.sh
```

### 2. Claude Desktop Config
**Location:** `claude_desktop_config.json`

Example configuration for Claude Desktop showing how to register the santa-clara MCP server using the wrapper script.

## Installation for Claude Desktop

### Option 1: Linux Users

1. Copy the wrapper config to Claude Desktop's config directory:
   ```bash
   mkdir -p ~/.config/Claude
   cp claude_desktop_config.json ~/.config/Claude/claude_desktop_config.json
   ```

2. Verify the absolute path in the config points to your installation:
   ```bash
   cat ~/.config/Claude/claude_desktop_config.json | grep santa-clara-wrapper
   ```

3. Restart Claude Desktop

### Option 2: Windows Users (via WSL)

1. Create the Claude config directory if it doesn't exist:
   ```bash
   mkdir -p /mnt/c/Users/YourUsername/AppData/Roaming/Claude
   ```

2. Copy the config file to Windows AppData:
   ```bash
   cp claude_desktop_config.json /mnt/c/Users/YourUsername/AppData/Roaming/Claude/claude_desktop_config.json
   ```

   Note: Replace `YourUsername` with your actual Windows username.

3. (Optional) If you prefer to use WSL bash directly without the wrapper, edit the config:
   ```json
   {
     "mcpServers": {
       "santa-clara-local": {
         "command": "bash",
         "args": [
           "-c",
           "exec /home/jcornell/mcp-dev-environment/scripts/santa-clara-wrapper.sh"
         ]
       }
     }
   }
   ```

4. Restart Claude Desktop

### Option 3: macOS Users

1. Copy the wrapper config to Claude Desktop's config directory:
   ```bash
   mkdir -p ~/Library/Application\ Support/Claude
   cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. Restart Claude Desktop

### Option 4: Manual Configuration

If you already have a `claude_desktop_config.json`, add this entry to your existing `mcpServers`:

```json
{
  "mcpServers": {
    "santa-clara-local": {
      "command": "bash",
      "args": [
        "/home/jcornell/mcp-dev-environment/scripts/santa-clara-wrapper.sh"
      ]
    }
  }
}
```

## How It Works

1. **Claude Desktop** starts the wrapper script via `bash` with stdio communication
2. **Wrapper script** receives JSON-RPC 2.0 requests on stdin
3. **Curl** sends the request to the HTTPS endpoint (`https://localhost:8443/santa-clara/mcp`)
4. **Santa-clara server** processes the MCP request (initialize, tools/list, tools/call)
5. **Response** flows back through curl to stdout where Claude Desktop reads it

## Supported MCP Methods

The wrapper supports all MCP JSON-RPC 2.0 methods implemented in the santa-clara server:

- **initialize** - Handshake with protocol version and capabilities
- **tools/list** - Returns available tools including `get_property_info`
- **tools/call** - Executes tools (e.g., get_property_info with APN input)

## Testing the Setup

### Test 1: Wrapper directly
```bash
# Test tools/list
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
  ./scripts/santa-clara-wrapper.sh | jq .

# Test initialize
echo '{"jsonrpc":"2.0","method":"initialize","id":2}' | \
  ./scripts/santa-clara-wrapper.sh | jq .

# Test tools/call
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_property_info","input":{"apn":"123-456-789"}},"id":3}' | \
  ./scripts/santa-clara-wrapper.sh | jq .
```

### Test 2: Via Claude Desktop

After configuring Claude Desktop:

1. Open Claude Desktop
2. Look for the santa-clara-local server in the MCP servers list
3. Try calling the get_property_info tool with a sample APN like "123-456-789"
4. You should receive property data for that APN

## Troubleshooting

### "Connection refused" error
- Verify the MCP stack is running: `docker compose ps`
- Ensure port 8443 is accessible: `curl -k https://localhost:8443/health`
- Check the absolute path in the config is correct

### "Certificate verify failed"
- The wrapper uses `-k` flag to skip certificate verification (safe for development)
- If you prefer to trust the certificate, install the mkcert CA:
  ```bash
  mkcert -install
  ```
- Then modify the wrapper to remove the `-k` flag (optional)

### Wrapper script not found
- Verify the script exists: `ls -la scripts/santa-clara-wrapper.sh`
- Confirm it's executable: `chmod +x scripts/santa-clara-wrapper.sh`
- Check the absolute path in the config matches your installation

### Claude Desktop not detecting the server
- Restart Claude Desktop completely (close and reopen)
- Check the Claude Desktop logs (usually in AppData/Roaming/Claude)
- Verify the command path is absolute (not relative)

## Performance Notes

- Each request goes through curl → HTTPS → Nginx → santa-clara server
- Response times are typically <100ms for simple requests
- For production use, consider direct stdio connections without HTTP wrapping

## Security Notes

⚠️ **Development Only**: This setup uses:
- Self-signed TLS certificates via mkcert
- `-k` flag to skip certificate verification in curl
- Localhost-only binding (127.0.0.1:8443)

For production:
- Use properly signed certificates
- Implement authentication/authorization
- Restrict access to the MCP endpoint
- Use environment-based configuration for sensitive data

## Additional Resources

- [MCP Protocol Spec](https://modelcontextprotocol.io)
- [Claude Desktop Documentation](https://claude.ai)
- [mkcert Documentation](https://github.com/FiloSottile/mkcert)
