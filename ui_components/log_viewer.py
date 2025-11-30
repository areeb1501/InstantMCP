"""
Log Viewer UI Component

Real-time deployment log viewer with filtering.
"""

import gradio as gr
from utils.database import get_db
from utils.models import Deployment, DeploymentHistory


def create_log_viewer():
    """
    Create the log viewer UI component.

    Returns:
        gr.Blocks: Log viewer interface
    """
    with gr.Blocks() as viewer:
        gr.Markdown("## 📝 Deployment Logs")
        gr.Markdown("View deployment history and events")

        # Filters
        with gr.Row():
            deployment_filter = gr.Dropdown(
                label="Filter by Deployment",
                choices=["All Deployments"],
                value="All Deployments",
                interactive=True,
                scale=2
            )
            action_filter = gr.Dropdown(
                label="Filter by Action",
                choices=["all", "created", "code_updated", "metadata_updated", "deleted", "security_scan_passed", "security_scan_warning"],
                value="all",
                interactive=True,
                scale=1
            )
            auto_refresh = gr.Checkbox(label="Auto-refresh", value=False, scale=0)
            refresh_btn = gr.Button("🔄 Refresh", size="sm", scale=0)

        # Log Display
        logs_display = gr.Code(
            language="shell",
            label="Event Logs",
            lines=25,
            interactive=False,
            value="Loading logs..."
        )

        # Log Stats
        with gr.Row():
            total_events = gr.Textbox(label="Total Events", interactive=False, scale=1)
            date_range = gr.Textbox(label="Date Range", interactive=False, scale=1)

        # Functions
        def load_deployment_list():
            """Load deployments for filter dropdown"""
            try:
                with get_db() as db:
                    deployments = Deployment.get_active_deployments(db)
                    choices = ["All Deployments"] + [
                        f"{dep.server_name} ({dep.deployment_id[:16]}...)"
                        for dep in deployments
                    ]
                    return gr.Dropdown(choices=choices)
            except Exception:
                return gr.Dropdown(choices=["All Deployments"])

        def load_logs(deployment_filter_val="All Deployments", action="all"):
            """Load and format deployment logs"""
            try:
                with get_db() as db:
                    query = db.query(DeploymentHistory)

                    # Filter by deployment if not "All"
                    if deployment_filter_val != "All Deployments" and "(" in deployment_filter_val:
                        # Extract deployment_id from filter value
                        dep_id_part = deployment_filter_val.split("(")[1].split("...")[0]
                        query = query.filter(DeploymentHistory.deployment_id.like(f"%{dep_id_part}%"))

                    # Filter by action if not "all"
                    if action != "all":
                        query = query.filter(DeploymentHistory.action == action)

                    # Get logs ordered by newest first
                    logs = query.order_by(DeploymentHistory.created_at.desc()).limit(100).all()

                    if not logs:
                        return (
                            "No logs found matching the selected filters.",
                            "0",
                            "N/A"
                        )

                    # Format logs
                    log_text = ""
                    for log in logs:
                        timestamp = log.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        dep_id_short = log.deployment_id[:20] + "..." if len(log.deployment_id) > 20 else log.deployment_id

                        # Format action with emoji
                        action_emoji = {
                            "created": "✨",
                            "deleted": "🗑️",
                            "code_updated": "📝",
                            "metadata_updated": "⚙️",
                            "security_scan_passed": "✅",
                            "security_scan_warning": "⚠️",
                            "pre_update_backup": "💾"
                        }.get(log.action, "📋")

                        log_text += f"[{timestamp}] {action_emoji} {log.action.upper()}\n"
                        log_text += f"  Deployment: {dep_id_short}\n"

                        # Add details if available
                        if log.details:
                            details_str = str(log.details)
                            if len(details_str) > 200:
                                details_str = details_str[:200] + "..."
                            log_text += f"  Details: {details_str}\n"

                        log_text += "\n"

                    # Calculate stats
                    total = len(logs)
                    oldest = logs[-1].created_at if logs else None
                    newest = logs[0].created_at if logs else None

                    if oldest and newest:
                        date_range_str = f"{oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}"
                    else:
                        date_range_str = "N/A"

                    return (
                        log_text or "No logs available",
                        str(total),
                        date_range_str
                    )

            except Exception as e:
                return (
                    f"Error loading logs: {str(e)}",
                    "0",
                    "N/A"
                )

        # Wire up events
        refresh_btn.click(
            fn=load_logs,
            inputs=[deployment_filter, action_filter],
            outputs=[logs_display, total_events, date_range],
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        deployment_filter.change(
            fn=load_logs,
            inputs=[deployment_filter, action_filter],
            outputs=[logs_display, total_events, date_range],
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        action_filter.change(
            fn=load_logs,
            inputs=[deployment_filter, action_filter],
            outputs=[logs_display, total_events, date_range],
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        # Load deployment list and logs on viewer load
        viewer.load(
            fn=load_deployment_list,
            outputs=deployment_filter,
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        viewer.load(
            fn=load_logs,
            outputs=[logs_display, total_events, date_range],
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

    return viewer
