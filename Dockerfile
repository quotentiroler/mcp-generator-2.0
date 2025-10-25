# Multi-stage Dockerfile for MCP Generator 2.0
# Optimized for production use

# Stage 1: Build stage
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for OpenAPI Generator
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install OpenAPI Generator CLI
RUN npm install -g @openapitools/openapi-generator-cli

# Copy project files
COPY pyproject.toml ./
COPY README.md ./
COPY mcp_generator/ ./mcp_generator/
COPY scripts/ ./scripts/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Stage 2: Runtime stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for OpenAPI Generator
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy OpenAPI Generator from builder
COPY --from=builder /usr/local/lib/node_modules/@openapitools/openapi-generator-cli /usr/local/lib/node_modules/@openapitools/openapi-generator-cli
RUN ln -s /usr/local/lib/node_modules/@openapitools/openapi-generator-cli/bin/openapi-generator-cli /usr/local/bin/openapi-generator-cli

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY mcp_generator/ ./mcp_generator/
COPY scripts/ ./scripts/
COPY pyproject.toml ./
COPY README.md ./

# Create directory for OpenAPI specs
RUN mkdir -p /app/specs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create non-root user
RUN useradd -m -u 1000 mcpgen && chown -R mcpgen:mcpgen /app
USER mcpgen

# Volume for OpenAPI specs and output
VOLUME ["/app/specs", "/app/output"]

# Default command
ENTRYPOINT ["generate-mcp"]
CMD ["--help"]

# Usage examples:
# Build: docker build -t mcp-generator .
# Run: docker run -v $(pwd)/specs:/app/specs -v $(pwd)/output:/app/output mcp-generator --file /app/specs/openapi.yaml
# Interactive: docker run -it --rm -v $(pwd):/app/specs mcp-generator sh
