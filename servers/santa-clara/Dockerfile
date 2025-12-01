FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# Make server executable
RUN chmod +x server.py

# Run as stdio server (not HTTP server)
CMD ["python", "-u", "server.py"]
