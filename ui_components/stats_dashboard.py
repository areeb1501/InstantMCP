"""
Statistics Dashboard UI Component

Analytics and visualization dashboard for deployments.
Refactored from the standalone stats_dashboard.py
"""

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional

from utils.database import get_db
from utils.models import Deployment
from utils.usage_tracker import (
    get_deployment_statistics,
    get_tool_usage_breakdown,
    get_usage_timeline,
    get_client_statistics,
)


# Helper Functions (prefixed with _ to hide from MCP auto-discovery)
def _get_deployment_list():
    """Get list of all active deployments for dropdown."""
    try:
        with get_db() as db:
            deployments = Deployment.get_active_deployments(db)
            if not deployments:
                return []
            return [f"{dep.server_name} ({dep.deployment_id})" for dep in deployments]
    except Exception:
        return []


def _extract_deployment_id(selection: str) -> Optional[str]:
    """Extract deployment_id from dropdown selection."""
    if not selection or "(" not in selection:
        return None
    return selection.split("(")[1].rstrip(")")


def _format_number(num):
    """Format large numbers with K, M suffixes."""
    if num is None:
        return "N/A"
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(int(num))


def _format_duration(ms):
    """Format milliseconds into human-readable duration."""
    if ms is None:
        return "N/A"
    if ms < 1000:
        return f"{int(ms)}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    return f"{minutes:.1f}m"


def _create_metric_card(title: str, value: str, subtitle: str = "") -> str:
    """Create an HTML metric card."""
    return f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 24px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 8px 0;
    ">
        <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">{title}</div>
        <div style="font-size: 32px; font-weight: bold; margin-bottom: 4px;">{value}</div>
        <div style="font-size: 12px; opacity: 0.8;">{subtitle}</div>
    </div>
    """


def _create_timeline_chart(deployment_id: str, days: int = 7):
    """Create timeline chart showing requests over time."""
    timeline = get_usage_timeline(deployment_id, days=days, granularity="day")

    if not timeline or len(timeline) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No usage data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="gray"))
        fig.update_layout(title="Requests Over Time", height=300)
        return fig

    df = pd.DataFrame(timeline)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['requests'], mode='lines+markers', name='Requests',
        line=dict(color='#667eea', width=3), marker=dict(size=8, color='#764ba2'),
        fill='tozeroy', fillcolor='rgba(102, 126, 234, 0.2)',
    ))

    fig.update_layout(
        title=f"Requests Over Time (Last {days} days)",
        xaxis_title="Date", yaxis_title="Requests", height=350,
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def _create_tool_usage_chart(deployment_id: str, days: int = 30):
    """Create bar chart for tool usage."""
    tools = get_tool_usage_breakdown(deployment_id, days=days, limit=10)

    if not tools or len(tools) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No tool usage data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="gray"))
        fig.update_layout(title="Top Tools Used", height=300)
        return fig

    df = pd.DataFrame(tools)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['count'], y=df['tool_name'], orientation='h',
        marker=dict(color=df['count'], colorscale='Viridis', showscale=False),
        text=df['count'], textposition='outside',
    ))

    fig.update_layout(
        title=f"Top Tools Used (Last {days} days)",
        xaxis_title="Number of Calls", yaxis_title="Tool Name",
        height=max(300, len(tools) * 40),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def _load_deployment_stats(deployment_selection: str, days: int = 30):
    """Load and display statistics for selected deployment."""
    if not deployment_selection:
        return ("<div style='text-align: center; padding: 40px; color: gray;'>Please select a deployment</div>", None, None, "")

    deployment_id = _extract_deployment_id(deployment_selection)
    if not deployment_id:
        return ("<div style='text-align: center; padding: 40px; color: red;'>Invalid deployment</div>", None, None, "")

    stats = get_deployment_statistics(deployment_id, days=days)
    if not stats:
        return ("<div style='text-align: center; padding: 40px; color: red;'>Failed to load statistics</div>", None, None, "")

    # Create metric cards
    total_requests = _format_number(stats.get('total_requests', 0))
    success_rate = stats.get('success_rate_percent', 0)
    avg_time = _format_duration(stats.get('avg_response_time_ms'))
    failed_requests = _format_number(stats.get('failed_requests', 0))

    metrics_html = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 20px 0;">
        {_create_metric_card("Total Requests", total_requests, f"Last {days} days")}
        {_create_metric_card("Success Rate", f"{success_rate:.1f}%", f"{failed_requests} failures")}
        {_create_metric_card("Avg Response Time", avg_time, "Per request")}
        {_create_metric_card("Active Period", f"{days} days", "Data retention")}
    </div>
    """

    # Get deployment info
    with get_db() as db:
        deployment = Deployment.get_by_deployment_id(db, deployment_id)
        if deployment:
            last_used = deployment.last_used_at.strftime("%Y-%m-%d %H:%M UTC") if deployment.last_used_at else "Never"
            created = deployment.created_at.strftime("%Y-%m-%d %H:%M UTC") if deployment.created_at else "Unknown"
            info_text = f"""
**Deployment Information**
- **Server Name:** {deployment.server_name}
- **Status:** {deployment.status}
- **Created:** {created}
- **Last Used:** {last_used}
- **URL:** {deployment.url}
            """
        else:
            info_text = "Deployment information not available"

    # Create charts
    timeline_chart = _create_timeline_chart(deployment_id, days)
    tool_chart = _create_tool_usage_chart(deployment_id, days)

    return (metrics_html, timeline_chart, tool_chart, info_text)


def create_stats_dashboard():
    """
    Create the statistics dashboard UI component.

    Returns:
        gr.Blocks: Stats dashboard interface
    """
    with gr.Blocks() as dashboard:
        gr.Markdown("## 📊 Statistics Dashboard")
        gr.Markdown("Monitor and analyze your deployed MCP servers")

        with gr.Row():
            with gr.Column(scale=3):
                deployment_dropdown = gr.Dropdown(
                    choices=_get_deployment_list(),
                    label="Select Deployment",
                    info="Choose a deployment to view its statistics",
                    interactive=True,
                )
            with gr.Column(scale=1):
                days_slider = gr.Slider(
                    minimum=1, maximum=90, value=30, step=1,
                    label="Time Range (days)",
                    info="Number of days to analyze"
                )
            with gr.Column(scale=1):
                refresh_btn = gr.Button("🔄 Refresh", variant="secondary", size="sm")

        # Metrics Cards
        metrics_html = gr.HTML(
            "<div style='text-align: center; padding: 40px; color: gray;'>Select a deployment to view statistics</div>"
        )

        # Charts Row
        with gr.Row():
            with gr.Column():
                timeline_plot = gr.Plot(label="Request Timeline")
            with gr.Column():
                tool_plot = gr.Plot(label="Tool Usage")

        # Deployment Info
        with gr.Accordion("📋 Deployment Details", open=False):
            deployment_info = gr.Markdown("Select a deployment to view details")

        # Event handlers
        def _update_stats(deployment, days):
            return _load_deployment_stats(deployment, int(days))

        deployment_dropdown.change(
            fn=_update_stats,
            inputs=[deployment_dropdown, days_slider],
            outputs=[metrics_html, timeline_plot, tool_plot, deployment_info],
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        days_slider.change(
            fn=_update_stats,
            inputs=[deployment_dropdown, days_slider],
            outputs=[metrics_html, timeline_plot, tool_plot, deployment_info],
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        refresh_btn.click(
            fn=lambda: gr.Dropdown(choices=_get_deployment_list()),
            outputs=[deployment_dropdown],
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

    return dashboard
