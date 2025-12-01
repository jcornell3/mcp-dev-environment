# MCP Server Development Guide

**For:** mcp-dev-environment  
**Date:** December 1, 2025  
**Status:** Production Ready  

---

## Overview

This guide shows you how to create Model Context Protocol (MCP) servers that integrate with Claude Desktop and other MCP clients. Based on real-world experience building the santa-clara property tax server.

---

## Prerequisites

- Completed Phase 1 & 2 of FRESH_WORKSTATION_SETUP.md
- mcp-dev-environment running
- Basic Python knowledge
- Understanding of async/await

---

## Quick Start: Create Your First MCP Server

### **Step 1: Create Server Directory**

```bash
cd ~/mcp-dev-environment/servers
mkdir my-server
cd my-server
```

### **Step 2: Create requirements.txt**

```
mcp>=1.0.0
```

That's it! The MCP SDK is all you need.

### **Step 3: Create server.py**

```python
#!/usr/bin/env python3
"""
My First MCP Server
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Initialize MCP server
app = Server("my-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="hello",
            description="Say hello to someone",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the person to greet"
                    }
                },
                "required": ["name"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a tool"""
    if name == "hello":
        person_name = arguments.get("name", "World")
        greeting = f"Hello, {person_name}! Welcome to MCP development."
        
        return [
            TextContent(
                type="text",
                text=greeting
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
```

### **Step 4: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
RUN chmod +x server.py

# CRITICAL: Use -u flag for unbuffered output
CMD ["python", "-u", "server.py"]
```

### **Step 5: Add to docker-compose.yml**

```yaml
services:
  # ... existing services ...
  
  my-server:
    build:
      context: ./servers/my-server
    container_name: mcp-dev-environment-my-server-1
    networks:
      - mcp-network
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

### **Step 6: Build and Test**

```bash
cd ~/mcp-dev-environment
docker compose build my-server
docker compose up -d my-server

# Test initialize
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | docker exec -i mcp-dev-environment-my-server-1 python -u /app/server.py

# Test tools/list
echo '{"jsonrpc":"2.0","method":"tools/list","id":2}' | docker exec -i mcp-dev-environment-my-server-1 python -u /app/server.py

# Test tools/call
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"hello","arguments":{"name":"Alice"}},"id":3}' | docker exec -i mcp-dev-environment-my-server-1 python -u /app/server.py
```

### **Step 7: Add to Claude Desktop**

Edit `C:\Users\USERNAME\AppData\Roaming\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "wsl",
      "args": [
        "docker",
        "exec",
        "-i",
        "mcp-dev-environment-my-server-1",
        "python",
        "-u",
        "/app/server.py"
      ]
    }
  }
}
```

Restart Claude Desktop and test!

---

## MCP Server Anatomy

### **Core Components**

```python
from mcp.server import Server              # Main server class
from mcp.server.stdio import stdio_server  # stdio transport
from mcp.types import Tool, TextContent    # Type definitions

# Create server instance
app = Server("server-name")

# Define tools
@app.list_tools()
async def list_tools() -> list[Tool]:
    pass

# Handle tool calls
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    pass

# Run server
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
```

---

## Tool Definition Best Practices

### **Good Tool Schema**

```python
Tool(
    name="get_user_info",  # Clear, descriptive name
    description="Retrieve user information by email address",  # What it does
    inputSchema={
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "User's email address",  # Describe the parameter
                "pattern": "^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$"  # Validation
            },
            "include_history": {
                "type": "boolean",
                "description": "Include user's activity history",
                "default": False  # Provide defaults
            }
        },
        "required": ["email"]  # Mark required fields
    }
)
```

### **Bad Tool Schema**

```python
Tool(
    name="get",  # Too vague
    description="Gets stuff",  # Not descriptive
    inputSchema={
        "type": "object",
        "properties": {
            "x": {  # Unclear parameter name
                "type": "string"  # No description
            }
        }
        # Missing 'required' array
    }
)
```

---

## Response Formatting

### **Text Responses**

```python
return [
    TextContent(
        type="text",
        text="Your formatted response here"
    )
]
```

### **Rich Responses with Data**

```python
# Format user-friendly text
formatted_text = f"""User Information
Email: {user['email']}
Name: {user['name']}
Status: {user['status']}
"""

# Return both text and structured data
return [
    TextContent(
        type="text",
        text=formatted_text
    )
]
```

---

## Error Handling

### **Validate Inputs**

```python
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "get_user_info":
        email = arguments.get("email")
        
        # Validate required parameters
        if not email:
            raise ValueError("Email is required")
        
        # Validate format
        if "@" not in email:
            raise ValueError("Invalid email format")
        
        # Process request
        user = get_user(email)
        
        if not user:
            raise ValueError(f"User not found: {email}")
        
        # Return result
        return [TextContent(type="text", text=f"Found user: {user['name']}")]
```

### **Handle Multiple Tools**

```python
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "tool_one":
        return handle_tool_one(arguments)
    elif name == "tool_two":
        return handle_tool_two(arguments)
    elif name == "tool_three":
        return handle_tool_three(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

def handle_tool_one(args: dict) -> list[TextContent]:
    # Tool-specific logic
    pass
```

---

## Testing Your Server

### **Unit Testing Structure**

```python
# tests/test_server.py
import pytest
import asyncio
from server import app

@pytest.mark.asyncio
async def test_list_tools():
    """Test tools are properly listed"""
    tools = await app._list_tools_handler()
    assert len(tools) > 0
    assert tools[0].name == "expected_tool_name"

@pytest.mark.asyncio
async def test_call_tool_success():
    """Test successful tool execution"""
    result = await app._call_tool_handler(
        "tool_name",
        {"param": "value"}
    )
    assert result[0].text == "expected output"

@pytest.mark.asyncio
async def test_call_tool_validation():
    """Test input validation"""
    with pytest.raises(ValueError):
        await app._call_tool_handler(
            "tool_name",
            {}  # Missing required params
        )
```

### **Manual Testing Commands**

```bash
# Store container name
CONTAINER="mcp-dev-environment-my-server-1"

# Test 1: Initialize
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | docker exec -i $CONTAINER python -u /app/server.py

# Test 2: List Tools
echo '{"jsonrpc":"2.0","method":"tools/list","id":2}' | docker exec -i $CONTAINER python -u /app/server.py

# Test 3: Call Tool
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"hello","arguments":{"name":"World"}},"id":3}' | docker exec -i $CONTAINER python -u /app/server.py
```

---

## Common Patterns

### **Pattern 1: Data Lookup Tool**

```python
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "lookup_data":
        query_id = arguments.get("id")
        
        # Fetch from database/API
        data = await fetch_data(query_id)
        
        # Format response
        formatted = format_data(data)
        
        return [TextContent(type="text", text=formatted)]
```

### **Pattern 2: Calculation Tool**

```python
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "calculate":
        value_a = arguments.get("a")
        value_b = arguments.get("b")
        operation = arguments.get("operation")
        
        # Perform calculation
        result = perform_calculation(value_a, value_b, operation)
        
        return [TextContent(type="text", text=f"Result: {result}")]
```

### **Pattern 3: Status Check Tool**

```python
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "check_status":
        service_name = arguments.get("service")
        
        # Check service status
        status = check_service(service_name)
        
        return [TextContent(
            type="text",
            text=f"Service {service_name}: {status['state']}\nUptime: {status['uptime']}"
        )]
```

---

## Advanced: Multiple Tools

### **Organizing Multiple Tools**

```python
# Define tool handlers separately
async def handle_user_info(args: dict) -> list[TextContent]:
    email = args.get("email")
    user = get_user(email)
    return [TextContent(type="text", text=format_user(user))]

async def handle_user_create(args: dict) -> list[TextContent]:
    email = args.get("email")
    name = args.get("name")
    user = create_user(email, name)
    return [TextContent(type="text", text=f"Created user: {user['id']}")]

async def handle_user_delete(args: dict) -> list[TextContent]:
    user_id = args.get("id")
    delete_user(user_id)
    return [TextContent(type="text", text=f"Deleted user: {user_id}")]

# Map tools to handlers
TOOL_HANDLERS = {
    "get_user_info": handle_user_info,
    "create_user": handle_user_create,
    "delete_user": handle_user_delete,
}

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handler = TOOL_HANDLERS.get(name)
    if handler:
        return await handler(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")
```

---

## Debugging

### **Enable Debug Logging**

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/server.log'),
        logging.StreamHandler()  # Also print to console
    ]
)

logger = logging.getLogger(__name__)

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    logger.debug(f"Tool called: {name}")
    logger.debug(f"Arguments: {arguments}")
    
    result = process_tool(name, arguments)
    
    logger.debug(f"Result: {result}")
    return result
```

### **Check Container Logs**

```bash
# View real-time logs
docker logs -f mcp-dev-environment-my-server-1

# View last 100 lines
docker logs --tail 100 mcp-dev-environment-my-server-1

# Search for errors
docker logs mcp-dev-environment-my-server-1 2>&1 | grep -i error
```

### **Common Issues**

| Symptom | Cause | Solution |
|---------|-------|----------|
| No response | Buffered output | Add `-u` flag to python command |
| "Tool not found" | Name mismatch | Check tool name in list_tools and call_tool |
| Timeout | Blocking operation | Use async/await properly |
| Invalid JSON | Syntax error in response | Validate JSON before returning |

---

## Performance Tips

### **1. Keep Tools Fast**

- Target < 100ms response time
- Use async for I/O operations
- Cache frequently accessed data

### **2. Optimize Data Fetching**

```python
# Bad: Sequential fetches
user = await get_user(user_id)
posts = await get_posts(user_id)
comments = await get_comments(user_id)

# Good: Parallel fetches
user, posts, comments = await asyncio.gather(
    get_user(user_id),
    get_posts(user_id),
    get_comments(user_id)
)
```

### **3. Limit Response Size**

```python
# Truncate large responses
MAX_LENGTH = 10000

if len(response_text) > MAX_LENGTH:
    response_text = response_text[:MAX_LENGTH] + "\n\n[Response truncated...]"
```

---

## Security Considerations

### **1. Input Validation**

```python
def validate_email(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_apn(apn: str) -> bool:
    """Validate APN format (e.g., 123-456-789)"""
    import re
    pattern = r'^\d{3}-\d{3}-\d{3}$'
    return re.match(pattern, apn) is not None
```

### **2. Rate Limiting**

```python
from collections import defaultdict
from datetime import datetime, timedelta

# Simple rate limiter
class RateLimiter:
    def __init__(self, max_calls: int, period: timedelta):
        self.max_calls = max_calls
        self.period = period
        self.calls = defaultdict(list)
    
    def allow(self, key: str) -> bool:
        now = datetime.now()
        cutoff = now - self.period
        
        # Remove old calls
        self.calls[key] = [t for t in self.calls[key] if t > cutoff]
        
        # Check limit
        if len(self.calls[key]) >= self.max_calls:
            return False
        
        # Record call
        self.calls[key].append(now)
        return True

# Usage
limiter = RateLimiter(max_calls=10, period=timedelta(minutes=1))

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if not limiter.allow(name):
        raise ValueError("Rate limit exceeded. Please try again later.")
    
    # Process tool...
```

### **3. Sanitize Outputs**

```python
def sanitize_output(text: str) -> str:
    """Remove sensitive information from output"""
    # Redact email addresses
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]', text)
    
    # Redact phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    
    # Redact SSN
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    
    return text
```

---

## Deployment Checklist

Before deploying your MCP server:

- [ ] All tools have clear descriptions
- [ ] Input schemas properly define required/optional fields
- [ ] Error handling covers edge cases
- [ ] Manual tests pass (initialize, tools/list, tools/call)
- [ ] Response times are acceptable (< 1s)
- [ ] Logging is configured
- [ ] Security considerations addressed
- [ ] Docker image builds successfully
- [ ] Container runs without errors
- [ ] Claude Desktop config tested
- [ ] Documentation updated

---

## Next Steps

1. **Build Your Server:** Use the quick start template
2. **Test Locally:** Use manual testing commands
3. **Integrate:** Add to Claude Desktop config
4. **Iterate:** Add more tools as needed
5. **Share:** Commit to repository

---

## Resources

- **MCP Specification:** https://modelcontextprotocol.io/
- **Python SDK Docs:** https://github.com/anthropics/mcp-python
- **Example Servers:** Check `servers/santa-clara/` for reference
- **Lessons Learned:** See MCP_DEVELOPMENT_LESSONS_LEARNED.md

---

**Document Version:** 1.0  
**Last Updated:** December 1, 2025  
