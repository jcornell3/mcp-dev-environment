# Docker Security & Caddy Reverse Proxy Implementation

**Date:** December 4, 2025
**Status:** Complete
**Version:** 1.0

---

## Overview

This document describes the Docker security improvements and Caddy reverse proxy integration for the MCP Development Environment. The changes transform the architecture from direct exposure of bridge services to a secure, production-ready setup with an ingress layer.

**Before:**
```
Public Internet → Bridge Services (0.0.0.0:3001-3005) → MCP Servers
```

**After:**
```
Public Internet → Caddy (0.0.0.0:80/443) → Bridge Services (127.0.0.1:3001-3005) → MCP Servers
```

---

## Task 1: Secure Port Bindings

### Change Summary

All bridge services have been updated to bind ports exclusively to `127.0.0.1` (localhost):

#### Before:
```yaml
bridge-math:
  ports:
    - "${BRIDGE_MATH_PORT:-3001}:3000"  # Exposed on 0.0.0.0
```

#### After:
```yaml
bridge-math:
  ports:
    - "127.0.0.1:${BRIDGE_MATH_PORT:-3001}:3000"  # Localhost only
```

### Services Updated

All 5 bridge services now use secure localhost binding:

| Service | Port | Binding |
|---------|------|---------|
| bridge-math | 3001 | 127.0.0.1:3001:3000 |
| bridge-santa-clara | 3002 | 127.0.0.1:3002:3000 |
| bridge-youtube-transcript | 3003 | 127.0.0.1:3003:3000 |
| bridge-youtube-to-mp3 | 3004 | 127.0.0.1:3004:3000 |
| bridge-github-remote | 3005 | 127.0.0.1:3005:3000 |

### Security Benefits

✅ **Prevents unauthorized external access** - Bridge servers only accessible from localhost
✅ **Reduces attack surface** - No direct exposure to internet traffic
✅ **Still allows local development** - Full access from host machine
✅ **VPS-friendly** - Ready for firewalled environments

---

## Task 2: Caddy Reverse Proxy Service

### Service Definition

Added new `caddy` service to `docker-compose.yml`:

```yaml
caddy:
  image: caddy:alpine
  ports:
    - "80:80"    # HTTP (publicly exposed)
    - "443:443"  # HTTPS (publicly exposed)
  volumes:
    - ./Caddyfile:/etc/caddy/Caddyfile:ro
    - caddy_data:/data
    - caddy_config:/config
  environment:
    - ACME_AGREE=true
  restart: unless-stopped
  depends_on:
    - bridge-math
    - bridge-santa-clara
    - bridge-youtube-transcript
    - bridge-youtube-to-mp3
    - bridge-github-remote
  networks:
    - mcp-network
```

### Key Features

| Feature | Value | Purpose |
|---------|-------|---------|
| Image | `caddy:alpine` | Lightweight, production-ready |
| HTTP Port | 80 | Public entry point |
| HTTPS Port | 443 | Secure public entry point |
| Caddyfile | Read-only mount | Configuration file |
| Cert Storage | `caddy_data` volume | Persistent Let's Encrypt certs |
| Config Storage | `caddy_config` volume | Caddy state persistence |
| Restart Policy | `unless-stopped` | Auto-restart on failures |

### Network Configuration

Added explicit Docker network for service discovery:

```yaml
networks:
  mcp-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

volumes:
  caddy_data:
  caddy_config:
```

This allows Caddy to reference bridge services by container name (e.g., `bridge-math:3000`).

---

## Task 3: Caddyfile Configuration

### Development Mode (Default)

The Caddyfile provides path-based routing for local development:

```caddy
http://localhost/math/* {
    reverse_proxy bridge-math:3000 {
        uri strip_prefix /math
    }
}
```

**Access Pattern:**
```
http://localhost/math/sse     → bridge-math:3000/sse
http://localhost/santa-clara  → bridge-santa-clara:3000
http://localhost/youtube-transcript → bridge-youtube-transcript:3000
```

### Production Mode (Documented)

The Caddyfile includes comprehensive production comments for subdomain-based routing:

```caddy
math.example.com {
    reverse_proxy bridge-math:3000
}

santa-clara.example.com {
    reverse_proxy bridge-santa-clara:3000
}
```

**Automatic Caddy Features:**
- ✅ Let's Encrypt certificate generation
- ✅ Automatic certificate renewal
- ✅ HTTP → HTTPS redirect
- ✅ ACME challenge handling

### Optional Security: Basic Auth

Example for adding authentication to services:

```caddy
math.example.com {
    basicauth /* {
        admin {$PASSWORD_HASH}
    }
    reverse_proxy bridge-math:3000
}
```

Generate hash: `caddy hash-password`

---

## Usage & Migration Guide

### Development (Current)

1. **Start services:**
   ```bash
   docker-compose up -d
   ```

2. **Access bridge services:**
   - Via Caddy: `http://localhost/math`
   - Direct (localhost only): `http://localhost:3001`

3. **Backward compatibility:**
   - Bridge services still accessible on 3001-3005 from localhost
   - Useful during migration and testing

### Production Migration

1. **Update Caddyfile:**
   - Uncomment production section
   - Replace `example.com` with actual domain
   - Add environment variables for auth (if needed)

2. **Configure DNS:**
   ```
   math.example.com          → VPS IP
   santa-clara.example.com   → VPS IP
   youtube-transcript.example.com → VPS IP
   youtube-to-mp3.example.com → VPS IP
   github-remote.example.com → VPS IP
   ```

3. **Open firewall ports:**
   ```bash
   # VPS firewall
   ufw allow 80/tcp
   ufw allow 443/tcp
   # Optionally close 3001-3005 (or keep 127.0.0.1-only for monitoring)
   ```

4. **Deploy:**
   ```bash
   docker-compose up -d
   ```

5. **Verify:**
   ```bash
   curl https://math.example.com
   ```

---

## Security Considerations

### Layer 1: Port Binding (127.0.0.1)

**What it does:** Restricts bridge services to localhost
**Who can access:** Only connections from the same host
**Trade-off:** Requires reverse proxy for external access

### Layer 2: Caddy Ingress

**What it does:** Single public entry point with TLS termination
**Who can access:** Anyone with correct domain + optional auth
**Trade-off:** Caddy becomes critical component (but it's very reliable)

### Layer 3: Internal Docker Network

**What it does:** Service-to-service communication via internal bridge network
**Who can access:** Only containers on the same network
**Trade-off:** Services can't talk to external services without explicit port publishing

### Optional Layer 4: Authentication

**What it does:** Basic HTTP auth or mTLS for sensitive services
**Who can access:** Users with valid credentials
**Trade-off:** Additional complexity, requires credential management

---

## Testing

### Local Development

```bash
# Test Caddy routing
curl http://localhost/math/sse
curl http://localhost/santa-clara/sse

# Test direct bridge access (still works for local only)
curl http://localhost:3001/sse
curl http://localhost:3002/sse
```

### Production

```bash
# Test HTTPS certificate
curl https://math.example.com

# Check certificate validity
echo | openssl s_client -connect math.example.com:443 | grep -A 5 "Issuer"

# View Caddy admin API
curl http://localhost:2019/config/
```

---

## Troubleshooting

### Caddy won't start
```bash
docker-compose logs caddy
# Check: Caddyfile syntax errors
# Fix: docker exec mcp-dev-environment-caddy-1 caddy fmt --overwrite /etc/caddy/Caddyfile
```

### Bridge services not accessible via Caddy
```bash
# Verify bridge services are running
docker-compose ps

# Check network connectivity
docker exec mcp-dev-environment-caddy-1 ping bridge-math

# Check reverse proxy configuration
docker exec mcp-dev-environment-caddy-1 caddy dump-config
```

### SSL certificate issues (production)
```bash
# Check certificate storage
docker exec mcp-dev-environment-caddy-1 ls /data/caddy/certificates/

# View Caddy logs
docker-compose logs caddy | grep -i "cert\|acme\|tls"
```

### localhost:3001-3005 not accessible
This is expected after the security update. To access directly:
```bash
# Only works from the same host
curl http://localhost:3001/sse

# From another machine, use Caddy:
curl http://localhost/math/sse
```

---

## Future Enhancements

1. **HTTP/2 Push** - Enable server push for better performance
2. **Rate Limiting** - Add Caddy rate limiting middleware
3. **Request Logging** - Structured logging to ELK stack
4. **Metrics** - Prometheus metrics from Caddy
5. **API Gateway Features** - Caching, request transformation, etc.
6. **mTLS** - Service-to-service encryption
7. **Web App Firewall** - ModSecurity integration (if needed)

---

## Files Modified/Created

| File | Change | Purpose |
|------|--------|---------|
| `docker-compose.yml` | Updated + Added | Port binding security + Caddy service |
| `Caddyfile` | Created | Reverse proxy configuration |

---

## References

- **Caddy Documentation:** https://caddyserver.com/docs/
- **Docker Port Publishing:** https://docs.docker.com/config/containers/container-networking/
- **Let's Encrypt:** https://letsencrypt.org/
- **Security Best Practices:** https://cheatsheetseries.owasp.org/

---

**Document Version:** 1.0
**Last Updated:** December 4, 2025
**Status:** Complete
