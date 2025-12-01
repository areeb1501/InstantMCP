# Webhook and Analytics Setup Guide

## Overview

The InstantMCP platform includes automatic usage tracking for all deployed MCP servers. When you deploy an MCP server to Modal, it automatically sends usage data (tool calls, response times, success/failure) back to your Gradio app via webhooks.

## How It Works

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Modal MCP     │         │   Webhook        │         │   Gradio App    │
│   Deployment    │────────>│   Endpoint       │────────>│   Database      │
│                 │  POST   │                  │  Store  │                 │
│  @mcp.tool()    │         │  /api/webhook/   │         │  UsageEvent     │
│  execution      │         │    usage         │         │  Analytics      │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

### Data Flow

1. **Deployment**: When you deploy an MCP server, the system:
   - Auto-detects your Gradio app's URL (HF Spaces or localhost)
   - Injects tracking code into your Modal deployment
   - Configures `MCP_WEBHOOK_URL` and `MCP_DEPLOYMENT_ID` environment variables

2. **Execution**: When a tool is called:
   - The tracking wrapper measures execution time
   - Captures success/failure status and error messages
   - Sends data to webhook endpoint (non-blocking)

3. **Storage**: The webhook endpoint:
   - Receives POST requests with usage data
   - Stores in PostgreSQL database (`usage_events` table)
   - Updates deployment statistics (total requests, avg response time)

4. **Analytics**: The dashboard:
   - Queries the database for deployment statistics
   - Displays real-time metrics, charts, and tables
   - Shows request volumes, success rates, tool usage, etc.

## Configuration

### Automatic (Recommended)

The system automatically detects your base URL:

**On Hugging Face Spaces:**
- Reads `SPACE_HOST` environment variable
- Constructs webhook URL: `https://{SPACE_HOST}/api/webhook/usage`
- No configuration needed! ✅

**Local Development:**
- Uses `http://localhost:{PORT}/api/webhook/usage`
- Default PORT is 7860
- Works out of the box for testing

### Manual Configuration

If you need to override the automatic detection:

**Option 1: Set `MCP_BASE_URL`**
```bash
# In .env file or HF Spaces secrets
MCP_BASE_URL=https://your-custom-domain.com
```

**Option 2: Set `MCP_WEBHOOK_URL` directly**
```bash
# In .env file or HF Spaces secrets
MCP_WEBHOOK_URL=https://your-custom-domain.com/api/webhook/usage
```

## Environment Variables

### Required for Hugging Face Spaces

Set these in **Space Settings → Variables and Secrets**:

```bash
# Database (Secret)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Modal deployment (Secrets)
MODAL_TOKEN_ID=your_modal_token_id
MODAL_TOKEN_SECRET=your_modal_token_secret
```

### Optional Configuration

```bash
# Webhook Configuration (usually auto-detected)
MCP_BASE_URL=https://your-app.hf.space  # Auto-detected on HF Spaces
MCP_WEBHOOK_URL=https://your-app.hf.space/api/webhook/usage  # Auto-constructed

# Webhook Control
MCP_WEBHOOK_ENABLED=true  # Enable/disable tracking

# Security (recommended for production)
MCP_WEBHOOK_SECRET=your_secret_key  # For HMAC signature validation
MCP_WEBHOOK_RATE_LIMIT=1000  # Requests per minute per deployment
```

## Testing the Webhook

### Method 1: Check Webhook Status

The platform exposes a status endpoint:

```bash
# Check if webhook is active
curl https://your-app.hf.space/api/webhook/status
```

Response:
```json
{
  "webhook_enabled": true,
  "webhook_url": "https://your-app.hf.space/api/webhook/usage",
  "message": "Webhook endpoint is active"
}
```

### Method 2: Python Test Script

Create a test script to verify webhook connectivity:

```python
import requests
from datetime import datetime

webhook_url = "https://your-app.hf.space/api/webhook/usage"

test_data = {
    'deployment_id': 'test-deployment',
    'tool_name': 'test_tool',
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'duration_ms': 150,
    'success': True,
    'error': None
}

response = requests.post(webhook_url, json=test_data, timeout=5)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

### Method 3: Use Built-in Test Function

```python
from utils.webhook_receiver import test_webhook_connection, get_webhook_info

# Get configuration info
info = get_webhook_info()
print(info)
# Output: {
#   'enabled': True,
#   'base_url': 'https://your-app.hf.space',
#   'webhook_url': 'https://your-app.hf.space/api/webhook/usage',
#   'environment': 'HuggingFace Spaces'
# }

# Test connection
result = test_webhook_connection()
print(result)
# Output: {
#   'success': True,
#   'message': 'Webhook endpoint is reachable',
#   'status_code': 200
# }
```

## Webhook Payload Format

When Modal deployments send data, they use this format:

```json
{
  "deployment_id": "deploy-mcp-example-abc123",
  "tool_name": "get_weather",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "duration_ms": 245,
  "success": true,
  "error": null
}
```

**Fields:**
- `deployment_id`: Unique deployment identifier
- `tool_name`: Name of the MCP tool function that was called
- `timestamp`: ISO 8601 UTC timestamp
- `duration_ms`: Execution time in milliseconds
- `success`: Boolean indicating success/failure
- `error`: Error message if `success=false`, otherwise `null`

## Viewing Analytics

After webhooks are working, view analytics in the **📊 Statistics** tab:

1. **Select a deployment** from the dropdown
2. **Choose time range** (7, 30, or 90 days)
3. **View metrics**:
   - Total Requests
   - Success Rate
   - Average Response Time
   - Failed Requests
4. **Analyze charts**:
   - Request Timeline (daily patterns)
   - Tool Usage Breakdown
   - Top Clients Table

## Troubleshooting

### Issue: No data showing in analytics dashboard

**Possible Causes:**
1. Webhook URL not configured properly
2. Modal deployments using old code (before tracking was added)
3. Database not receiving webhook calls

**Solutions:**
1. Check webhook configuration:
   ```python
   from utils.webhook_receiver import get_webhook_info
   print(get_webhook_info())
   ```

2. Redeploy your MCP server to get updated tracking code:
   ```python
   # Use the update_deployment_code() tool
   # Or delete and redeploy the server
   ```

3. Check webhook endpoint:
   ```bash
   curl https://your-app.hf.space/api/webhook/status
   ```

4. Check Modal deployment logs:
   ```bash
   modal app logs your-app-name
   ```
   Look for: "✅ Tracking enabled" or "⚠️ No webhook URL"

### Issue: Webhook returns 404

**Cause:** The webhook endpoint is not mounted properly in FastAPI.

**Solution:** Ensure `app.py` includes:
```python
@fastapi_app.post("/api/webhook/usage")
async def webhook_usage(request: Request):
    # Webhook handler code
    ...
```

### Issue: Modal deployments can't reach webhook

**Possible Causes:**
1. Network/firewall blocking Modal → HF Spaces
2. Webhook URL points to localhost instead of public URL
3. HF Space is in sleep mode

**Solutions:**
1. Verify webhook URL is public:
   ```python
   from utils.webhook_receiver import get_webhook_url
   url = get_webhook_url()
   print(url)  # Should be https://, not http://localhost
   ```

2. Wake up your HF Space by visiting it

3. Check Modal can reach your space:
   ```bash
   # From Modal app logs
   modal app logs your-app-name --follow
   ```

### Issue: Tracking disabled message

If you see "⚠️ No webhook URL - tracking disabled" in Modal logs:

**Cause:** `MCP_WEBHOOK_URL` environment variable not set in Modal deployment.

**Solution:** This should be automatically set during deployment. If not:

1. Check the deployment code includes webhook configuration
2. Redeploy with latest code
3. Verify environment variables in Modal dashboard

## Security Best Practices

### 1. Use HMAC Signature Validation (Recommended)

Generate a webhook secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add to HF Spaces secrets:
```bash
MCP_WEBHOOK_SECRET=your_generated_secret
```

### 2. Rate Limiting

Set rate limits to prevent abuse:
```bash
MCP_WEBHOOK_RATE_LIMIT=1000  # Max 1000 requests per minute per deployment
```

### 3. Network Restrictions

Consider restricting webhook endpoint to Modal's IP ranges (if available).

## Advanced Configuration

### Custom Webhook Handler

You can extend the webhook handler to add custom logic:

```python
@fastapi_app.post("/api/webhook/usage")
async def webhook_usage(request: Request):
    try:
        data = await request.json()
        
        # Custom validation
        if not validate_webhook_data(data):
            return JSONResponse({"success": False, "error": "Invalid data"})
        
        # Store in database
        with db_transaction() as db:
            UsageEvent.record_usage(db=db, **data)
        
        # Custom actions (e.g., send alerts)
        if data.get('success') == False:
            send_error_alert(data)
        
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})
```

### Multiple Webhook Endpoints

You can send data to multiple endpoints:

```python
# In Modal deployment tracking code
WEBHOOK_URLS = [
    os.getenv('MCP_WEBHOOK_URL'),
    os.getenv('BACKUP_WEBHOOK_URL'),
    os.getenv('ANALYTICS_WEBHOOK_URL')
]

def _send_tracking(tool_name, duration_ms, success, error=None):
    for webhook_url in WEBHOOK_URLS:
        if webhook_url:
            try:
                requests.post(webhook_url, json=data, timeout=2)
            except:
                pass  # Silent failure
```

## FAQ

**Q: Does tracking add latency to tool calls?**
A: No. Tracking uses non-blocking `requests.post()` with 2-second timeout. If the webhook is slow/unavailable, it silently fails without affecting your tool.

**Q: What happens if the webhook endpoint is down?**
A: Tracking fails silently. Your MCP tools continue working normally. When the webhook comes back online, new calls will be tracked.

**Q: Can I disable tracking for a specific deployment?**
A: Yes. Set `MCP_WEBHOOK_ENABLED=false` in the deployment environment or remove the webhook URL configuration.

**Q: How much database storage does tracking use?**
A: Each event is ~200-500 bytes. For 1M requests/month: ~500MB. Plan accordingly.

**Q: Can I export analytics data?**
A: Yes. Query the `usage_events` table directly, or use the provided functions:
```python
from utils.usage_tracker import get_deployment_statistics
stats = get_deployment_statistics(deployment_id, days=30)
```

**Q: Does tracking work with local Modal development?**
A: Yes! The webhook URL auto-detects `http://localhost:7860` for local testing. Your local Gradio app receives the webhooks.

## Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review Modal deployment logs: `modal app logs your-app-name`
3. Test webhook connectivity with built-in functions
4. Check Gradio app logs for webhook errors
5. Open an issue on GitHub with:
   - Webhook configuration output
   - Modal deployment logs
   - Error messages
