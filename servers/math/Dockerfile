FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# Make server executable
RUN chmod +x server.py

# Expose port 3000 for HTTP/SSE
EXPOSE 3000

# Run as HTTP server with FastAPI
CMD ["python", "-u", "server.py"]
