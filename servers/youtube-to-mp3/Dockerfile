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

COPY server.py mcp_logic.py ./
RUN chmod +x server.py

RUN mkdir -p /app/downloads

CMD ["python", "-u", "server.py"]
