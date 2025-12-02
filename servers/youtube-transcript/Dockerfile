FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py mcp_logic.py ./
RUN chmod +x server.py

CMD ["python", "-u", "server.py"]
