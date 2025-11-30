"""
Automatic Usage Tracking - Wraps @mcp.tool() decorator to track all tool calls
"""

SIMPLE_TRACKING_CODE = '''
# ============================================================================
# AUTOMATIC USAGE TRACKING
# ============================================================================
import os
import requests
import time
from datetime import datetime
from functools import wraps

WEBHOOK_URL = os.getenv('MCP_WEBHOOK_URL', '')
DEPLOYMENT_ID = os.getenv('MCP_DEPLOYMENT_ID', 'unknown')

def _send_tracking(tool_name, duration_ms, success, error=None):
    """Send tracking data to webhook endpoint"""
    if not WEBHOOK_URL:
        return

    try:
        requests.post(WEBHOOK_URL, json={
            'deployment_id': DEPLOYMENT_ID,
            'tool_name': tool_name,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'duration_ms': duration_ms,
            'success': success,
            'error': error
        }, timeout=2)
    except:
        pass  # Silent failure (fix Later)

# Save the original mcp.tool decorator
_original_tool_decorator = mcp.tool

def _tracking_tool_decorator(*dec_args, **dec_kwargs):
    """Wraps @mcp.tool() to automatically track all tool calls"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_msg = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                duration_ms = int((time.time() - start_time) * 1000)
                _send_tracking(func.__name__, duration_ms, success, error_msg)

        # Apply the original FastMCP decorator to our tracking wrapper
        return _original_tool_decorator(*dec_args, **dec_kwargs)(wrapper)

    return decorator

# Replace mcp.tool with our tracking version
mcp.tool = _tracking_tool_decorator

if WEBHOOK_URL:
    print(f"✅ Tracking enabled: {WEBHOOK_URL}")
    print(f"📍 Deployment ID: {DEPLOYMENT_ID}")
else:
    print("⚠️  No webhook URL - tracking disabled")
'''

def get_tracking_code():
    return SIMPLE_TRACKING_CODE
