# Pin Python version — never use "latest" in production
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Layer 1: dependencies (cached unless requirements.txt changes)
# This is the most important Docker optimization
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Layer 2: application code
COPY api/ ./api/
COPY src/ ./src/
COPY configs/ ./configs/
COPY models/ ./models/

# Drop root privileges — never run as root in production
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check — Docker will mark the container unhealthy if this fails
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

ENV WORKERS=4
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers $WORKERS"]