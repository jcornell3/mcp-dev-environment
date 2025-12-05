FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py mcp_logic.py ./
RUN chmod +x server.py

# Expose port 3000 for HTTP/SSE
EXPOSE 3000

CMD ["python", "-u", "server.py"]
