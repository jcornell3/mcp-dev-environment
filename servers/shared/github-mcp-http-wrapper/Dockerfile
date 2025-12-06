FROM node:24-slim

# Install GitHub MCP server binary
RUN apt-get update && \
    apt-get install -y curl && \
    curl -L https://github.com/github/github-mcp-server/releases/download/v0.24.0/github-mcp-server-linux-amd64 -o /usr/local/bin/github-mcp-server && \
    chmod +x /usr/local/bin/github-mcp-server && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Setup wrapper application
WORKDIR /app
COPY package.json .
RUN npm install --production

COPY server.js .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
  CMD node -e "require('http').get('http://localhost:' + (process.env.PORT || 3000) + '/health', (r) => { if (r.statusCode !== 200) throw new Error(r.statusCode) })"

# Start wrapper
CMD ["node", "server.js"]
