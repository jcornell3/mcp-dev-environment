# MCP Bridges for Cloudflare Workers

This directory contains bridge scripts that enable Claude Desktop to communicate with Cloudflare-hosted MCP servers.

## Overview

Since Claude Desktop only supports stdio-based communication, we need bridge scripts that:
1. Read JSON-RPC messages from stdin (from Claude Desktop)
2. Convert them to HTTP requests
3. Send them to Cloudflare Workers
4. Convert HTTP responses back to stdout
5. Handle notifications (204 No Content) properly

## Available Bridges

### PowerShell Bridge (Windows) - **RECOMMENDED FOR PRODUCTION**

**File**: `mcp-cloud-bridge.ps1`
**Location on system**: `C:\Users\jcorn\mcp-cloud-bridge.ps1`
**Language**: PowerShell
**Platforms**: Windows (WSL or native PowerShell)

**Features**:
- ✅ Reads JSON-RPC from stdin
- ✅ Forwards to Cloudflare Workers via HTTPS
- ✅ Handles byte array to UTF-8 string conversion
- ✅ Logs all requests/responses (per-worker log files)
- ✅ Properly handles 204 No Content responses
- ✅ Prevents "Unexpected End of JSON" errors

**Configuration in Claude Desktop**:
```json
{
  "math-cloud": {
    "command": "powershell.exe",
    "args": [
      "-NoProfile",
      "-ExecutionPolicy", "Bypass",
      "-File", "C:\\Users\\jcorn\\mcp-cloud-bridge.ps1",
      "-Url", "https://math.tamshai.workers.dev",
      "-AuthToken", "7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3"
    ]
  },
  "santa-clara-cloud": {
    "command": "powershell.exe",
    "args": [
      "-NoProfile",
      "-ExecutionPolicy", "Bypass",
      "-File", "C:\\Users\\jcorn\\mcp-cloud-bridge.ps1",
      "-Url", "https://santa-clara.tamshai.workers.dev",
      "-AuthToken": "6c2da9cf361a0d83b0306de7064cbd2fefceda59cdfe51ff300245f2cacf8ca9"
    ]
  }
}
```

**Log Files**:
- `C:\Users\jcorn\mcp-cloud-bridge-math.log` - Math worker logs
- `C:\Users\jcorn\mcp-cloud-bridge-santa-clara.log` - Santa Clara worker logs

### Node.js Bridge (Cross-Platform) - **FOR TESTING/DEVELOPMENT**

**File**: `cloudflare-bridge.js`
**Language**: Node.js/JavaScript
**Platforms**: Linux, macOS, Windows (with Node.js)

**Features**:
- ✅ Reads JSON-RPC from stdin
- ✅ Forwards to Cloudflare Workers
- ✅ Handles 204 No Content responses (silently)
- ✅ Cross-platform compatibility

**Usage**:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | node cloudflare-bridge.js math
```

**Configuration in Claude Desktop**:
```json
{
  "math-cloud": {
    "command": "node",
    "args": [
      "/home/jcornell/mcp-dev-environment/cloudflare-bridge.js",
      "math"
    ]
  }
}
```

### Bash Wrapper (Legacy)

**File**: `cloudflare-wrapper.sh`
**Language**: Bash
**Status**: Legacy (not recommended)

## Key Implementation Details

### Notification Handling (Critical)

Per JSON-RPC 2.0 specification:
- **Regular requests** (with `id` field) → Return HTTP 200 with JSON response
- **Notifications** (without `id` field) → Return HTTP 204 No Content (empty response)

**Important**: The bridge must NOT output empty lines for notifications, as this causes "Unexpected End of JSON input" errors.

**PowerShell bridge implementation**:
```powershell
# Only output non-empty responses (skip 204 No Content notifications)
if ($responseText.Trim()) {
    [Console]::Out.WriteLine($responseText)
    [Console]::Out.Flush()
}
```

**Node.js bridge implementation**:
```javascript
// Handle 204 No Content responses (for notifications)
if (res.statusCode === 204 || !data.trim()) {
    // Notifications don't get responses, so just exit silently
    if (callback) callback();
    return;
}
```

## Workers Configuration

Both workers are deployed to Cloudflare and configured to:
1. Accept Bearer token authentication
2. Handle JSON-RPC 2.0 requests properly
3. Return 204 No Content for notifications (no `id` field)
4. Properly detect `id: 0` as a valid request ID (not a notification)

**Math Worker**:
- URL: https://math.tamshai.workers.dev
- Tools: `calculate`, `factorial`
- Auth Token: `7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3`

**Santa Clara Worker**:
- URL: https://santa-clara.tamshai.workers.dev
- Tools: `get_property_info`
- Auth Token: `6c2da9cf361a0d83b0306de7064cbd2fefceda59cdfe51ff300245f2cacf8ca9`

## Testing

### Test PowerShell Bridge Directly
```powershell
$request = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
$request | powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\jcorn\mcp-cloud-bridge.ps1" -Url "https://math.tamshai.workers.dev" -AuthToken "7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3"
```

### Test Node.js Bridge Directly
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | node cloudflare-bridge.js math
```

### Test Worker Endpoints Directly
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 7dce5a53644f336c48a36bf095ef65c09dcbd4e7363d4771f525e811742d33b3" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  https://math.tamshai.workers.dev
```

## Troubleshooting

### "Unexpected End of JSON input" Error
- **Cause**: Bridge outputting empty lines for 204 No Content responses
- **Solution**: Ensure bridge checks for empty responses before outputting
- **PowerShell fix**: Use `if ($responseText.Trim())` before `WriteLine()`
- **Node.js fix**: Check `res.statusCode === 204` before JSON parsing

### Bridge Not Responding
- Check that Cloudflare Workers are accessible from your network
- Verify authentication tokens are correct
- Check bridge log files for detailed error messages
- Test worker endpoints directly with curl

### Log File Issues
- PowerShell bridge creates per-worker log files automatically
- Log files are UTF-16 LE encoded (use PowerShell or text editor that supports this)
- Check logs: `C:\Users\jcorn\mcp-cloud-bridge-*.log`

## Deployment History

Latest commits:
- `b29cbd0` - Add PowerShell MCP bridge to repository version control
- `9cb7e07` - Add PowerShell bridge empty response handling documentation
- `a525907` - Add PowerShell MCP bridge to repository version control
- `bd6f3a3` - Fix PowerShell bridge to not output empty lines for 204 responses
- `1c6a938` - Add final deployment status report
- `6a3a37e` - Fix Node.js bridge to handle 204 No Content responses
- `d46110d` - Redeploy Cloudflare Workers with notification fix
- `8e6d144` - Fix Workers response crossing and JSON-RPC 2.0 compliance

## Next Steps

1. **Verify bridge is working**: Test with the commands above
2. **Restart Claude Desktop**: Clear any cached error states
3. **Monitor logs**: Check per-worker log files for issues
4. **Test tools**: Try using math calculator and santa clara property info

All bridges are now fully functional and JSON-RPC 2.0 compliant.
