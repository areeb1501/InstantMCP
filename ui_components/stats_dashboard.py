"""
Statistics Dashboard UI Component

Analytics and visualization dashboard for deployments.
"""

import gradio as gr
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from utils.usage_tracker import (
    get_deployment_statistics,
    get_tool_usage_breakdown,
    get_usage_timeline,
    get_client_statistics,
    get_all_deployments_stats,
)
from utils.database import get_db
from utils.models import Deployment


def get_active_deployment_list() -> list:
    """Get list of active deployments for dropdown."""
    try:
        with get_db() as db:
            deployments = Deployment.get_active_deployments(db)
            if not deployments:
                return [("No deployments found", "")]
            return [
                (f"{dep.server_name} ({dep.deployment_id})", dep.deployment_id)
                for dep in deployments
            ]
    except Exception as e:
        print(f"Error getting deployments: {e}")
        return [("Error loading deployments", "")]


def format_number(num: Optional[float]) -> str:
    """Format number with K/M suffix."""
    if num is None:
        return "N/A"
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(int(num))


def create_metric_card(title: str, value: str, subtitle: str = "", color: str = "#06b6d4") -> str:
    """Create HTML for a metric card."""
    return f"""
    <div style="
        background: linear-gradient(135deg, {color}15, {color}05);
        border: 2px solid {color}40;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    ">
        <div style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
            {title}
        </div>
        <div style="font-size: 32px; font-weight: 700; color: {color}; margin-bottom: 4px;">
            {value}
        </div>
        <div style="color: #64748b; font-size: 12px;">
            {subtitle}
        </div>
    </div>
    """


def create_timeline_chart(deployment_id: str, days: int) -> go.Figure:
    """Create interactive timeline chart of requests."""
    try:
        timeline_data = get_usage_timeline(deployment_id, days, granularity="day")
        
        if not timeline_data or len(timeline_data) == 0:
            # Return empty chart with message
            fig = go.Figure()
            fig.add_annotation(
                text="No usage data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16, color="#94a3b8")
            )
            fig.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            return fig
        
        dates = [datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')) for item in timeline_data]
        requests = [item['requests'] for item in timeline_data]
        
        fig = go.Figure()
        
        # Add area chart
        fig.add_trace(go.Scatter(
            x=dates,
            y=requests,
            mode='lines',
            name='Requests',
            line=dict(color='#06b6d4', width=3),
            fill='tozeroy',
            fillcolor='rgba(6, 182, 212, 0.1)',
            hovertemplate='<b>%{x|%b %d}</b><br>Requests: %{y}<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(
                text=f"Request Timeline ({days} days)",
                font=dict(size=16, weight=600, color="#1e293b")
            ),
            height=300,
            margin=dict(l=20, r=20, t=60, b=40),
            xaxis=dict(
                title="Date",
                showgrid=True,
                gridcolor='rgba(0,0,0,0.05)',
            ),
            yaxis=dict(
                title="Requests",
                showgrid=True,
                gridcolor='rgba(0,0,0,0.05)',
            ),
            paper_bgcolor="white",
            plot_bgcolor="white",
            hovermode='x unified',
        )
        
        return fig
        
    except Exception as e:
        print(f"Error creating timeline chart: {e}")
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error loading data: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="#ef4444")
        )
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
        return fig


def create_tool_usage_chart(deployment_id: str, days: int) -> go.Figure:
    """Create bar chart of tool usage."""
    try:
        tools_data = get_tool_usage_breakdown(deployment_id, days, limit=10)
        
        if not tools_data or len(tools_data) == 0:
            fig = go.Figure()
            fig.add_annotation(
                text="No tool usage data",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16, color="#94a3b8")
            )
            fig.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            return fig
        
        tool_names = [item['tool_name'] for item in tools_data]
        counts = [item['count'] for item in tools_data]
        
        # Reverse for better display (highest at top)
        tool_names = tool_names[::-1]
        counts = counts[::-1]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=tool_names,
            x=counts,
            orientation='h',
            marker=dict(
                color=counts,
                colorscale='Teal',
                showscale=False,
            ),
            text=counts,
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Calls: %{x}<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(
                text="Top Tools by Usage",
                font=dict(size=16, weight=600, color="#1e293b")
            ),
            height=max(300, len(tool_names) * 40),
            margin=dict(l=20, r=20, t=60, b=40),
            xaxis=dict(
                title="Number of Calls",
                showgrid=True,
                gridcolor='rgba(0,0,0,0.05)',
            ),
            yaxis=dict(
                showgrid=False,
            ),
            paper_bgcolor="white",
            plot_bgcolor="white",
        )
        
        return fig
        
    except Exception as e:
        print(f"Error creating tool usage chart: {e}")
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error loading data: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="#ef4444")
        )
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
        return fig


def load_dashboard_data(
    deployment_id: str,
    days: int
) -> Tuple[str, str, str, str, go.Figure, go.Figure, str]:
    """Load all dashboard data for a deployment."""
    if not deployment_id:
        empty_fig = go.Figure()
        empty_fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
        return (
            create_metric_card("Total Requests", "—", "Select a deployment"),
            create_metric_card("Success Rate", "—", "Select a deployment", "#10b981"),
            create_metric_card("Avg Response Time", "—", "Select a deployment", "#f59e0b"),
            create_metric_card("Failed Requests", "—", "Select a deployment", "#ef4444"),
            empty_fig,
            empty_fig,
            "<div style='text-align: center; padding: 40px; color: #94a3b8;'>Select a deployment to view statistics</div>"
        )
    
    try:
        # Get statistics
        stats = get_deployment_statistics(deployment_id, days)
        
        if not stats:
            error_html = "<div style='text-align: center; padding: 40px; color: #ef4444;'>Error loading statistics</div>"
            empty_fig = go.Figure()
            empty_fig.update_layout(height=300)
            return (
                create_metric_card("Total Requests", "Error"),
                create_metric_card("Success Rate", "Error", "", "#10b981"),
                create_metric_card("Avg Response Time", "Error", "", "#f59e0b"),
                create_metric_card("Failed Requests", "Error", "", "#ef4444"),
                empty_fig,
                empty_fig,
                error_html
            )
        
        # Create metric cards
        total_requests = format_number(stats.get('total_requests', 0))
        success_rate = f"{stats.get('success_rate_percent', 0):.1f}%"
        avg_time = stats.get('avg_response_time_ms')
        avg_time_str = f"{avg_time:.0f}ms" if avg_time else "N/A"
        failed_requests = format_number(stats.get('failed_requests', 0))
        
        requests_card = create_metric_card(
            "Total Requests",
            total_requests,
            f"in last {days} days"
        )
        
        success_card = create_metric_card(
            "Success Rate",
            success_rate,
            f"{format_number(stats.get('successful_requests', 0))} successful",
            "#10b981"
        )
        
        response_card = create_metric_card(
            "Avg Response Time",
            avg_time_str,
            "per request",
            "#f59e0b"
        )
        
        failed_card = create_metric_card(
            "Failed Requests",
            failed_requests,
            f"{100 - stats.get('success_rate_percent', 0):.1f}% failure rate",
            "#ef4444"
        )
        
        # Create charts
        timeline_chart = create_timeline_chart(deployment_id, days)
        tool_chart = create_tool_usage_chart(deployment_id, days)
        
        # Create client statistics table
        clients_data = get_client_statistics(deployment_id, days, limit=10)
        
        if clients_data and len(clients_data) > 0:
            client_rows = "".join([
                f"""
                <tr style="border-bottom: 1px solid #e5e7eb;">
                    <td style="padding: 12px; color: #1e293b;">{client['client_id'] or 'Unknown'}</td>
                    <td style="padding: 12px; text-align: right; font-weight: 600; color: #06b6d4;">{client['count']}</td>
                </tr>
                """
                for client in clients_data[:10]
            ])
            
            clients_html = f"""
            <div style="background: white; border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden;">
                <div style="padding: 16px; border-bottom: 1px solid #e5e7eb; background: #f8fafc;">
                    <h3 style="margin: 0; font-size: 16px; font-weight: 600; color: #1e293b;">Top Clients</h3>
                </div>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f8fafc; border-bottom: 2px solid #e5e7eb;">
                            <th style="padding: 12px; text-align: left; font-weight: 600; color: #64748b; font-size: 12px; text-transform: uppercase;">Client ID</th>
                            <th style="padding: 12px; text-align: right; font-weight: 600; color: #64748b; font-size: 12px; text-transform: uppercase;">Requests</th>
                        </tr>
                    </thead>
                    <tbody>
                        {client_rows}
                    </tbody>
                </table>
            </div>
            """
        else:
            clients_html = "<div style='text-align: center; padding: 40px; color: #94a3b8; background: white; border-radius: 12px; border: 1px solid #e5e7eb;'>No client data available</div>"
        
        return (
            requests_card,
            success_card,
            response_card,
            failed_card,
            timeline_chart,
            tool_chart,
            clients_html
        )
        
    except Exception as e:
        print(f"Error loading dashboard data: {e}")
        error_html = f"<div style='text-align: center; padding: 40px; color: #ef4444;'>Error: {str(e)}</div>"
        empty_fig = go.Figure()
        empty_fig.update_layout(height=300)
        return (
            create_metric_card("Error", "—"),
            create_metric_card("Error", "—", "", "#10b981"),
            create_metric_card("Error", "—", "", "#f59e0b"),
            create_metric_card("Error", "—", "", "#ef4444"),
            empty_fig,
            empty_fig,
            error_html
        )


def create_stats_dashboard():
    """
    Create the statistics dashboard UI component.

    Returns:
        gr.Blocks: Stats dashboard interface
    """
    with gr.Blocks() as dashboard:
        gr.Markdown("## 📊 Analytics Dashboard")
        gr.Markdown("Monitor and analyze your deployed MCP servers in real-time")
        
        with gr.Row():
            with gr.Column(scale=2):
                deployment_dropdown = gr.Dropdown(
                    label="Select Deployment",
                    choices=get_active_deployment_list(),
                    value=None,
                    interactive=True,
                )
            with gr.Column(scale=1):
                days_dropdown = gr.Dropdown(
                    label="Time Range",
                    choices=[
                        ("Last 7 days", 7),
                        ("Last 30 days", 30),
                        ("Last 90 days", 90),
                    ],
                    value=30,
                    interactive=True,
                )
            with gr.Column(scale=0, min_width=120):
                refresh_btn = gr.Button("🔄 Refresh", variant="primary", size="lg")
        
        # Metrics cards
        with gr.Row():
            metric1 = gr.HTML()
            metric2 = gr.HTML()
            metric3 = gr.HTML()
            metric4 = gr.HTML()
        
        # Charts
        with gr.Row():
            timeline_chart = gr.Plot(label="Request Timeline")
        
        with gr.Row():
            with gr.Column(scale=1):
                tool_chart = gr.Plot(label="Tool Usage")
            with gr.Column(scale=1):
                client_table = gr.HTML()
        
        # Load data on deployment or time range change
        def refresh_data(deployment_id, days):
            return load_dashboard_data(deployment_id, days)
        
        # Refresh deployment list
        def refresh_deployments():
            return gr.Dropdown(choices=get_active_deployment_list())
        
        # Event handlers
        deployment_dropdown.change(
            fn=refresh_data,
            inputs=[deployment_dropdown, days_dropdown],
            outputs=[
                metric1, metric2, metric3, metric4,
                timeline_chart, tool_chart, client_table
            ],
            show_api=False
        )
        
        days_dropdown.change(
            fn=refresh_data,
            inputs=[deployment_dropdown, days_dropdown],
            outputs=[
                metric1, metric2, metric3, metric4,
                timeline_chart, tool_chart, client_table
            ],
            show_api=False
        )
        
        refresh_btn.click(
            fn=refresh_data,
            inputs=[deployment_dropdown, days_dropdown],
            outputs=[
                metric1, metric2, metric3, metric4,
                timeline_chart, tool_chart, client_table
            ],
            show_api=False
        ).then(
            fn=refresh_deployments,
            outputs=[deployment_dropdown],
            show_api=False
        )
        
        # Load initial empty state
        dashboard.load(
            fn=lambda: load_dashboard_data("", 30),
            outputs=[
                metric1, metric2, metric3, metric4,
                timeline_chart, tool_chart, client_table
            ],
            show_api=False
        )
    
    return dashboard
