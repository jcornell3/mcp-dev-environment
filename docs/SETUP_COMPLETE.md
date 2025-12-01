# MCP Development Environment — Setup Complete

This repository and local environment have been provisioned and a small MCP (mock control plane) stack is running locally.

## What was built

- Directory layout under `~/mcp-dev-environment`:
  - `nginx/` — Nginx Dockerfile and configuration (`nginx.conf`, `conf.d/mcp-servers.conf`).
  - `servers/santa-clara/` — example Python MCP server (Flask) with `app.py`, `Dockerfile`, `requirements.txt`, and tests.
  - `certs/` — mkcert-generated TLS certificates for `localhost` (`localhost.pem`, `localhost-key.pem`).
  - `logs/diagnostics/` — collected diagnostics and logs captured during setup.
  - `scripts/` — helper scripts including `scripts/test.sh` to run the Python tests.
  - `docker-compose.yml` — defines `nginx` reverse-proxy and `santa-clara` service.
  - `Makefile` and `.env` — convenience commands and environment variables.
  - `.gitignore` — ignores common artifacts.

## Services running and ports

- `nginx` (container name: `nginx-1`) — reverse proxy that terminates TLS and forwards traffic to the MCP server.
  - Container port: 443 (inside container)
  - Host port: 8443 (mapped via `.env` to avoid host port 443 conflicts)
  - Configured to proxy `/` and `/health` to the MCP service.

- `santa-clara` (container name: `santa-clara-1`) — example MCP server (Flask + gunicorn).
  - Exposes port 8000 internally (proxied by Nginx). Not directly mapped to a host port.

Confirmed endpoints (working):

- https://localhost:8443/ → {"service":"santa-clara","status":"running"}
- https://localhost:8443/health → {"status":"ok"}

Certificate note: TLS certs were created with `mkcert` and placed in `certs/`. `mkcert -install` was run, so the local dev CA should be trusted by your OS/browser.

## How to start / stop / manage the stack

All commands run from the working directory `~/mcp-dev-environment`

- Build & start (detached):
  - `make start`
  - or: `docker compose up -d --build`

- Stop and remove containers:
  - `make stop`
  - or: `docker compose down --remove-orphans`

- Restart:
  - `make restart`

- Follow logs:
  - `make logs` (follows `docker compose logs -f`)

- Build only:
  - `make build`

- Run the example server tests:
  - `make test` (runs `./scripts/test.sh`, which runs pytest for the example server)

## How to test endpoints

- From the machine running the stack (in a terminal):

```
curl -sSk https://localhost:8443/        # should return the service JSON
curl -sSk https://localhost:8443/health  # should return {"status":"ok"}

# Follow logs to watch startup or troubleshoot
make logs
```

- From a browser: visit `https://localhost:8443/` — your browser should trust the mkcert certificate if `mkcert -install` succeeded.

## Diagnostics and troubleshooting

- Diagnostics and logs captured during setup are available in:
  - `logs/diagnostics/compose-logs-after-rebuild.txt`
  - `logs/diagnostics/compose-logs.txt`
  - `logs/diagnostics/errors-after-rebuild.txt`
  - `logs/diagnostics/summary-errors-tail.txt`

- If ports conflict on your machine, update `.env`:
  - `HTTP_PORT` and `HTTPS_PORT` (default set to `80` and `8443` respectively in this environment).

## Next steps — Connecting Claude Desktop

To route Claude Desktop (or any local client) through this MCP reverse-proxy so it can reach the `santa-clara` service or a local model endpoint, follow these general steps:

1. Configure the client/upstream URL to point at the proxy:
   - Example: set the endpoint to `https://localhost:8443/` in the client's network/proxy settings.

2. Trust the local certificate (if needed):
   - `mkcert -install` was run during setup. If Claude Desktop runs under a different user or environment, ensure the mkcert root CA is trusted in that context (OS keychain or app-specific trust).

3. If the client expects a model routing header or environment variable, set the corresponding variable in your deployment or client configuration (for example, `DEFAULT_MODEL=claude-haiku-4.5`) and/or configure the MCP routing layer to forward requests appropriately.

4. If Claude Desktop requires API keys or auth, configure the MCP to accept and forward those credentials, or configure Claude Desktop to use any local auth mock you provide.

5. Test from Claude Desktop by pointing it at `https://localhost:8443/` and verifying requests are proxied to the `santa-clara` service.

If you want, I can add an example proxy route or an authentication shim in `servers/shared/` to demonstrate forwarding headers and API keys for Claude Desktop.

---

## Claude Desktop client configuration example

Follow these steps to point Claude Desktop at the local MCP reverse-proxy.

1. Configure Claude Desktop to connect to the local MCP server:
   - Set the server/endpoint URL to `https://localhost:8443/`.
2. Example JSON to place in `claude_desktop_config.json`:

```json
{
  "server": {
    "url": "https://localhost:8443/",
    "insecure_skip_verify": true
  },
  "auth": {
    "api_key": "YOUR_API_KEY_IF_NEEDED"
  }
}
```

 - `insecure_skip_verify: true` tells the client to ignore certificate verification for development when using mkcert; prefer trusting the mkcert CA in the OS instead of using this in production.

3. Where to put the config on Windows (typical locations):
   - User profile: `%APPDATA%\\ClaudeDesktop\\claude_desktop_config.json`
   - If the app uses ProgramData: `%PROGRAMDATA%\\ClaudeDesktop\\claude_desktop_config.json`
   - Or the installation directory where Claude Desktop stores config (check the app's documentation).

4. Restart Claude Desktop:
   - Close the Claude Desktop application (right-click the tray icon -> Exit, or use Task Manager to end the process).
   - Start Claude Desktop again from the Start menu or its shortcut.
   - Confirm in the app's network/settings area that it's pointing to `https://localhost:8443/`.

If you want, I can add a small sample `claude_desktop_config.json` into `servers/shared/` for testing, and instructions to load it on Windows.

If you want me to commit this, run the stack, or add example client config for Claude Desktop (or to wire in an actual model server), tell me which next step to take and I'll implement it.
