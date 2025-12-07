FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    wget \
    ca-certificates \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py mcp_logic.py google_drive.py ./
RUN chmod +x server.py

RUN mkdir -p /app/downloads
RUN mkdir -p /app/credentials

# Expose port 3000 for HTTP/SSE
EXPOSE 3000

CMD ["python", "-u", "server.py"]
