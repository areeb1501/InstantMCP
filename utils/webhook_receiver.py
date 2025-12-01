"""
Simple Webhook Configuration for MCP Usage Tracking

Provides basic configuration functions for the webhook endpoint.
The actual webhook endpoint is defined in app.py.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_base_url() -> str:
    """
    Auto-detect the base URL for the application.
    
    Checks in order:
    1. MCP_BASE_URL environment variable (explicit override)
    2. SPACE_HOST for Hugging Face Spaces
    3. Fallback to localhost for local development
    
    Returns:
        str: Base URL (e.g., 'https://mcp-1st-birthday-instantmcp.hf.space')
    """
    # Check for explicit override
    base_url = os.getenv('MCP_BASE_URL')
    if base_url:
        return base_url.rstrip('/')
    
    # Check if running on Hugging Face Spaces
    space_host = os.getenv('SPACE_HOST')
    if space_host:
        # HF Spaces provides SPACE_HOST without protocol
        return f"https://{space_host}"
    
    # Fallback to localhost for local development
    port = os.getenv('PORT', '7860')
    return f"http://localhost:{port}"


def get_webhook_url() -> str:
    """
    Get the configured webhook URL for usage tracking.
    
    Returns:
        str: Full webhook URL (e.g., 'https://your-app.hf.space/api/webhook/usage')
    """
    # Check for explicit webhook URL override
    webhook_url = os.getenv('MCP_WEBHOOK_URL')
    if webhook_url:
        return webhook_url
    
    # Build webhook URL from base URL
    base_url = get_base_url()
    return f"{base_url}/api/webhook/usage"


def is_webhook_enabled() -> bool:
    """Check if webhook endpoint is enabled"""
    return os.getenv('MCP_WEBHOOK_ENABLED', 'true').lower() == 'true'
