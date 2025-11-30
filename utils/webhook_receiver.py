"""
Simple Webhook Configuration for MCP Usage Tracking

Provides basic configuration functions for the webhook endpoint.
The actual webhook endpoint is defined in app.py.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_webhook_url() -> str:
    """Get the configured webhook URL"""
    base_url = os.getenv('MCP_BASE_URL', 'http://localhost:7860')
    return f"{base_url}/api/webhook/usage"


def is_webhook_enabled() -> bool:
    """Check if webhook endpoint is enabled"""
    return os.getenv('MCP_WEBHOOK_ENABLED', 'true').lower() == 'true'
