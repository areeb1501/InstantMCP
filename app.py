#!/usr/bin/env python3
"""
Gradio MCP Deployment Platform

A unified Gradio application that serves both:
1. MCP tools via SSE endpoint at /gradio_api/mcp/
2. Interactive web UI for deployment management and analytics

For Gradio Hackathon
"""

import gradio as gr
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# Import MCP tool functions
from mcp_tools.deployment_tools import (
    deploy_mcp_server,
    list_deployments,
    get_deployment_status,
    delete_deployment,
    get_deployment_code
)
from mcp_tools.stats_tools import (
    get_deployment_stats,
    get_tool_usage,
    get_all_stats_summary
)
from mcp_tools.security_tools import scan_deployment_security

# Import webhook configuration
from utils.webhook_receiver import get_webhook_url, is_webhook_enabled

# Import all UI components
from ui_components.admin_panel import create_admin_panel
from ui_components.code_editor import create_code_editor
from ui_components.ai_chat_deployment import create_ai_chat_deployment
from ui_components.stats_dashboard import create_stats_dashboard
from ui_components.log_viewer import create_log_viewer


# ============================================================================
# CUSTOM PROFESSIONAL THEME
# ============================================================================
class MCPTheme(gr.themes.Base):
    """Professional theme for MCP Deployment Platform"""
    def __init__(
        self,
        *,
        primary_hue=gr.themes.colors.cyan,
        secondary_hue=gr.themes.colors.emerald,
        neutral_hue=gr.themes.colors.slate,
        spacing_size=gr.themes.sizes.spacing_lg,
        radius_size=gr.themes.sizes.radius_md,
        text_size=gr.themes.sizes.text_md,
        font=(
            gr.themes.GoogleFont("Inter"),
            "ui-sans-serif",
            "system-ui",
            "sans-serif",
        ),
        font_mono=(
            gr.themes.GoogleFont("JetBrains Mono"),
            "ui-monospace",
            "monospace",
        ),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )

# Create theme instance with professional styling
mcp_theme = MCPTheme().set(
    # Clean background
    body_background_fill="*neutral_50",
    body_background_fill_dark="*neutral_900",
    # Modern buttons with cyan-to-emerald gradient
    button_primary_background_fill="linear-gradient(135deg, *primary_600, *secondary_600)",
    button_primary_background_fill_hover="linear-gradient(135deg, *primary_500, *secondary_500)",
    button_primary_text_color="white",
    button_primary_background_fill_dark="linear-gradient(135deg, *primary_700, *secondary_700)",
    # Clean blocks
    block_background_fill="white",
    block_background_fill_dark="*neutral_800",
    block_border_width="1px",
    block_label_text_weight="600",
    # Input styling
    input_background_fill="*neutral_50",
    input_background_fill_dark="*neutral_900",
)

# Custom CSS for better styling
custom_css = """
/* Main container */
.gradio-container {
    max-width: 1400px !important;
    margin: 0 auto !important;
    padding: 2rem 1rem !important;
}

/* Header styling */
.header-section {
    text-align: center;
    margin-bottom: 2.5rem;
    padding: 2rem 1rem;
    background: linear-gradient(135deg, #06b6d4 0%, #10b981 100%);
    border-radius: 16px;
    color: white;
}

.header-title {
    font-size: 2.75rem;
    font-weight: 800;
    margin-bottom: 0.75rem;
    letter-spacing: -0.02em;
}

.header-subtitle {
    font-size: 1.125rem;
    opacity: 0.95;
    max-width: 700px;
    margin: 0 auto;
    line-height: 1.6;
}

/* Tab styling */
.tab-nav {
    border-bottom: 2px solid #e5e7eb;
    margin-bottom: 1.5rem;
}

.tab-nav button {
    font-weight: 600;
    font-size: 0.95rem;
    padding: 0.75rem 1.5rem;
}

/* Footer styling */
.footer-section {
    margin-top: 3rem;
    padding-top: 2rem;
    border-top: 1px solid #e5e7eb;
    text-align: center;
    color: #6b7280;
    font-size: 0.875rem;
}

.footer-section code {
    background: #f3f4f6;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.875rem;
}

/* Improve spacing */
.block {
    margin-bottom: 1rem;
}

/* Button improvements */
button {
    transition: all 0.2s ease;
}

button:hover {
    transform: translateY(-1px);
}

/* ============================================
   TAB CONTENT CONSISTENCY FIX
   ============================================ */

/* Ensure all tab panels have consistent sizing */
.tabitem {
    width: 100% !important;
    max-width: 100% !important;
    min-height: 600px !important;
}

/* Ensure tab content fills the space properly */
.tabitem > .block,
.tabitem > div {
    width: 100% !important;
}

/* Fix for nested Blocks within tabs */
.tabitem .gradio-container {
    max-width: 100% !important;
    padding: 1rem !important;
}

/* Ensure rows stay full width */
.tabitem .row {
    width: 100% !important;
    gap: 1rem !important;
}

/* Ensure columns don't collapse */
.tabitem .column {
    min-width: 0 !important;
    flex: 1 1 auto !important;
}

/* Prevent content from shrinking */
.tabitem .wrap {
    width: 100% !important;
}
"""

# Create main application with tabs
with gr.Blocks(title="Instant MCP - AI-Powered MCP Deployment") as gradio_app:
    # Modern Header
    with gr.Row(elem_classes="header-section"):
        with gr.Column():
            gr.Markdown(
                '<div class="header-title">⚡ Instant MCP</div>',
                elem_classes="header-title"
            )
            gr.Markdown(
                '<div class="header-subtitle">From Idea to Production in Seconds • AI-powered deployment platform to build, deploy, and scale your MCP servers instantly</div>',
                elem_classes="header-subtitle"
            )

    # Tabbed interface
    with gr.Tabs():
        # Admin Panel Tab - Main deployment management
        with gr.Tab("⚙️ Admin Panel"):
            admin_panel = create_admin_panel()

        # Code Editor Tab - Edit deployment code
        with gr.Tab("💻 Code Editor"):
            code_editor = create_code_editor()

        # AI Assistant Tab - Chat interface for AI-powered deployment
        with gr.Tab("🤖 AI Assistant"):
            ai_chat = create_ai_chat_deployment()

        # Stats Dashboard Tab - Analytics and visualizations
        with gr.Tab("📊 Statistics"):
            stats_dashboard = create_stats_dashboard()

        # Log Viewer Tab - Deployment history and events
        with gr.Tab("📝 Logs"):
            log_viewer = create_log_viewer()

    # Professional Footer
    with gr.Row(elem_classes="footer-section"):
        with gr.Column():
            gr.Markdown(
                """
                **MCP SSE Endpoint**: `/gradio_api/mcp/` •
                **Documentation**: [Model Context Protocol](https://github.com/modelcontextprotocol) •
                Built with [Gradio](https://gradio.app)
                """
            )

    # ============================================================================
    # EXPLICIT MCP TOOL REGISTRATION
    # ============================================================================
    # Explicitly register ONLY the intended MCP tools (prevents UI handlers from being exposed)
    # All UI event handlers now use show_api=False to prevent exposure

    # Deployment Management Tools
    gr.api(deploy_mcp_server, api_name="deploy_mcp_server")
    gr.api(list_deployments, api_name="list_deployments")
    gr.api(get_deployment_status, api_name="get_deployment_status")
    gr.api(delete_deployment, api_name="delete_deployment")
    gr.api(get_deployment_code, api_name="get_deployment_code")

    # Statistics Tools
    gr.api(get_deployment_stats, api_name="get_deployment_stats")
    gr.api(get_tool_usage, api_name="get_tool_usage")
    gr.api(get_all_stats_summary, api_name="get_all_stats_summary")

    # Security Tools
    gr.api(scan_deployment_security, api_name="scan_deployment_security")

# Total tools registered (for logging)
total_tools = 9


# ============================================================================
# WEBHOOK ENDPOINT SETUP
# ============================================================================

# Create a custom FastAPI app for webhook routes
from fastapi import Request
from starlette.responses import JSONResponse

fastapi_app = FastAPI(title="MCP Deployment Platform API")

@fastapi_app.post("/api/webhook/usage")
async def webhook_usage(request: Request):
    """Simple webhook endpoint - just stores the data"""
    try:
        data = await request.json()

        from utils.database import db_transaction
        from utils.models import UsageEvent

        with db_transaction() as db:
            UsageEvent.record_usage(
                db=db,
                deployment_id=data.get('deployment_id'),
                tool_name=data.get('tool_name'),
                duration_ms=data.get('duration_ms'),
                success=data.get('success', True),
                error_message=data.get('error'),
                metadata={'source': 'webhook'}
            )

        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@fastapi_app.get("/api/webhook/status")
async def webhook_status():
    """Get webhook endpoint status and configuration"""
    return JSONResponse({
        "webhook_enabled": is_webhook_enabled(),
        "webhook_url": get_webhook_url(),
        "message": "Webhook endpoint is active" if is_webhook_enabled() else "Webhook endpoint is disabled"
    })

# Mount Gradio app onto FastAPI with MCP server enabled
app = gr.mount_gradio_app(
    fastapi_app, 
    gradio_app, 
    path="/", 
    mcp_server=True,
    theme=mcp_theme,
    css=custom_css
)


# Launch configuration
if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment (HF Spaces uses PORT=7860)
    port = int(os.environ.get("PORT", 7860))

    # Startup banner
    print("=" * 70)
    print("🚀 MCP Deployment Platform")
    print("=" * 70)
    print(f"📊 Web UI:           http://0.0.0.0:{port}")
    print(f"📡 MCP Endpoint:     http://0.0.0.0:{port}/gradio_api/mcp")
    print(f"📚 API Docs:         http://0.0.0.0:{port}/docs")
    print(f"🔗 Webhook Endpoint: http://0.0.0.0:{port}/api/webhook/usage")
    print("=" * 70)
    print(f"\n✅ Registered {total_tools} MCP tool endpoints")
    print("\n🎯 MCP Tools Available:")
    print("   • deploy_mcp_server")
    print("   • list_deployments")
    print("   • get_deployment_status")
    print("   • delete_deployment")
    print("   • get_deployment_code")
    print("   • get_deployment_stats")
    print("   • get_tool_usage")
    print("   • get_all_stats_summary")
    print("   • scan_deployment_security")
    print("\n💡 Connect via MCP client:")
    print(f'   Claude Desktop: {{"url": "http://localhost:{port}/gradio_api/mcp"}}')
    print("\n🎨 Web UI Features:")
    print("   • Admin Panel: Deploy & manage servers")
    print("   • Code Editor: View & edit deployment code")
    print("   • AI Assistant: Chat with Claude to create/modify MCPs")
    print("   • Statistics: Analytics & visualizations")
    print("   • Logs: Deployment history & events")
    print("=" * 70)

    # Run with uvicorn for production deployment
    # 'app' is the FastAPI app with Gradio mounted
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

