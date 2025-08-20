# =============================================================================
# SEED Agent Dockerfile - Multi-stage build for optimized container
# =============================================================================

FROM python:3.11-slim as builder

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# =============================================================================
# Runtime stage
# =============================================================================

FROM python:3.11-slim as runtime

# Set runtime arguments
ARG DEBIAN_FRONTEND=noninteractive

# Create non-root user
RUN groupadd -r seed && useradd -r -g seed seed

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/seed/.local

# Copy application code
COPY --chown=seed:seed . .

# Copy core modules from v2 (adapt existing code)
COPY --chown=seed:seed v2/core ./core
COPY --chown=seed:seed v2/fetchers ./fetchers

# Create required directories
RUN mkdir -p /app/logs && chown -R seed:seed /app/logs

# Set Python path and PATH
ENV PYTHONPATH=/app
ENV PATH=/home/seed/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER seed

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Default command - run both server and worker
CMD ["python", "seed-agent.py", "--mode", "both", "--host", "0.0.0.0", "--port", "8080"]