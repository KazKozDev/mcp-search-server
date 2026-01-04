# Use Python 3.12 Alpine image for smaller size
FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Install system dependencies needed for some Python packages
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    build-base

# Copy dependency files
COPY pyproject.toml ./
COPY README.md ./

# Copy source code
COPY src/ ./src/

# Install the package and its dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir uvicorn starlette

# Expose port (Smithery uses 8081, but we'll make it configurable)
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Run the HTTP server
CMD ["python", "-m", "mcp_search_server.http_server"]
