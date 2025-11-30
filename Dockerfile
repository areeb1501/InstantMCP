# Dockerfile for Gradio MCP Deployment Platform
# Optimized for Hugging Face Spaces Docker deployment
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - git: Required for Modal CLI and version control
# - curl: For health checks and HTTP requests
# - build-essential: Required for compiling some Python packages (psycopg2)
# - libpq-dev: PostgreSQL development libraries for psycopg2
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker caching)
COPY requirements.txt .

# Install Python dependencies
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user for HF Spaces compatibility
# HF Spaces runs containers as user with uid 1000
RUN useradd -m -u 1000 user

# Create necessary directories with proper permissions
RUN mkdir -p /app/deployments /home/user/.modal && \
    chown -R user:user /app /home/user/.modal

# Copy application code and required directories
COPY --chown=user:user app.py .
COPY --chown=user:user README.md .
COPY --chown=user:user mcp_tools/ ./mcp_tools/
COPY --chown=user:user ui_components/ ./ui_components/
COPY --chown=user:user utils/ ./utils/
#COPY --chown=user:user images/ ./images/

# Switch to non-root user
USER user

# Set home directory for the user
ENV HOME=/home/user

# Expose port 7860 (Gradio's default port, also used by Hugging Face Spaces)
EXPOSE 7860

# Set environment variables for Gradio
ENV PYTHONUNBUFFERED=1 \
    PORT=7860 \
    GRADIO_SERVER_NAME="0.0.0.0" \
    GRADIO_SERVER_PORT=7860 \
    GRADIO_MCP_SERVER=True

# Health check
# Checks if Gradio app is responding on the specified port
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-7860}/ || exit 1

# Startup script
# 1. Configure Modal authentication if credentials are provided
# 2. Launch Gradio app with MCP server enabled
CMD if [ -n "$MODAL_TOKEN_ID" ] && [ -n "$MODAL_TOKEN_SECRET" ]; then \
        echo "🔐 Configuring Modal authentication..."; \
        modal token set --token-id "$MODAL_TOKEN_ID" --token-secret "$MODAL_TOKEN_SECRET"; \
    fi && \
    echo "🚀 Starting Gradio MCP Deployment Platform..." && \
    echo "📊 Web UI will be available at: http://0.0.0.0:${PORT:-7860}" && \
    echo "📡 MCP endpoint will be at: http://0.0.0.0:${PORT:-7860}/gradio_api/mcp/" && \
    python app.py
