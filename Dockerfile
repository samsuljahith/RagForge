# RAGForge API Server
# Build:  docker build -t ragforge .
# Run:    docker run -p 8000:8000 ragforge

FROM python:3.11-slim

LABEL maintainer="RAGForge Contributors"
LABEL description="RAGForge API server — language-agnostic RAG platform"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY ragforge/ ragforge/
COPY examples/ examples/

# Install the package with API dependencies
RUN pip install --no-cache-dir -e ".[api]"

# Expose the API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the API server
CMD ["uvicorn", "ragforge.api:app", "--host", "0.0.0.0", "--port", "8000"]
