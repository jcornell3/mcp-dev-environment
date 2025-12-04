FROM node:20-alpine

WORKDIR /app

# Install docker cli
RUN apk add --no-cache docker-cli

# Copy the test server scripts
COPY simple-test-server.js .
COPY real-test-bridge.js .

# Expose port 3000
EXPOSE 3000

# Run the real test bridge (forwards to actual MCP servers)
CMD ["node", "real-test-bridge.js"]
