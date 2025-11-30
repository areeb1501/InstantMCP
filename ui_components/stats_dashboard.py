"""
Statistics Dashboard UI Component

Analytics and visualization dashboard for deployments.
"""

import gradio as gr


def create_stats_dashboard():
    """
    Create the statistics dashboard UI component.

    Returns:
        gr.Blocks: Stats dashboard interface
    """
    with gr.Blocks() as dashboard:
        gr.Markdown("## 📊 Statistics Dashboard")
        gr.Markdown("Monitor and analyze your deployed MCP servers")

        # Coming Soon message with styling
        gr.HTML("""
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 400px;
                padding: 60px 20px;
                text-align: center;
            ">
                <div style="
                    font-size: 72px;
                    margin-bottom: 24px;
                ">📊</div>
                <h2 style="
                    font-size: 36px;
                    font-weight: bold;
                    margin-bottom: 16px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                ">Coming Soon!</h2>
                <p style="
                    font-size: 18px;
                    color: #666;
                    max-width: 500px;
                    line-height: 1.6;
                ">
                    We're working on powerful analytics and visualization tools 
                    to help you monitor your MCP server deployments.
                </p>
                <div style="
                    margin-top: 32px;
                    padding: 16px 24px;
                    background: rgba(102, 126, 234, 0.1);
                    border-radius: 12px;
                    border: 1px solid rgba(102, 126, 234, 0.2);
                ">
                    <p style="margin: 0; color: #667eea; font-size: 14px;">
                        Features in development: Request analytics, Tool usage breakdown, Performance metrics
                    </p>
                </div>
            </div>
        """)

    return dashboard
