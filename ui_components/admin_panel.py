"""
Admin Panel UI Component

Interactive UI for managing MCP server deployments.
"""

import gradio as gr
from mcp_tools.deployment_tools import (
    deploy_mcp_server,
    list_deployments,
    delete_deployment,
    get_deployment_status
)


def create_admin_panel():
    """
    Create the admin panel UI component.

    Returns:
        gr.Blocks: Admin panel interface
    """
    with gr.Blocks() as panel:
        gr.Markdown("## ⚙️ Deployment Management")
        gr.Markdown("Deploy and manage your MCP servers")

        # Quick Deploy Section
        with gr.Accordion("➕ Quick Deploy", open=True):
            with gr.Row():
                with gr.Column(scale=2):
                    server_name = gr.Textbox(
                        label="Server Name",
                        placeholder="my-mcp-server",
                        info="Unique name for your MCP server"
                    )
                    code = gr.Code(
                        language="python",
                        label="MCP Tools Code",
                        lines=12,
                        value='''from fastmcp import FastMCP

mcp = FastMCP("cat-facts")

@mcp.tool()
def get_cat_fact() -> str:
    """Get a random cat fact from an API"""
    import requests
    response = requests.get("https://catfact.ninja/fact")
    return response.json()["fact"]

@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b
'''
                    )
                with gr.Column(scale=1):
                    packages = gr.Textbox(
                        label="Extra Packages",
                        placeholder="requests, pandas",
                        value="requests",
                        info="Comma-separated pip packages"
                    )
                    description = gr.Textbox(
                        label="Description",
                        lines=2,
                        placeholder="Optional description"
                    )

                    # New metadata fields
                    with gr.Row():
                        category = gr.Textbox(
                            label="Category",
                            placeholder="e.g., Weather, Finance",
                            value="Uncategorized",
                            scale=1
                        )
                        version = gr.Textbox(
                            label="Version",
                            value="1.0.0",
                            scale=1
                        )

                    tags = gr.Textbox(
                        label="Tags (comma-separated)",
                        placeholder="e.g., api, data, utilities"
                    )
                    author = gr.Textbox(
                        label="Author",
                        value="Anonymous"
                    )

                    deploy_btn = gr.Button("🚀 Deploy", variant="primary", size="lg")

            deploy_output = gr.JSON(label="Deployment Result")

            # Helper function to parse tags
            def deploy_with_metadata(name, code_val, pkgs, desc, cat, tag_str, auth, ver):
                """Deploy with metadata, parsing tags from comma-separated string"""
                tag_list = [t.strip() for t in tag_str.split(",") if t.strip()] if tag_str else []
                return deploy_mcp_server(
                    server_name=name,
                    mcp_tools_code=code_val,
                    extra_pip_packages=pkgs,
                    description=desc,
                    category=cat,
                    tags=tag_list,
                    author=auth,
                    version=ver
                )

            # Wire up deploy button
            deploy_btn.click(
                fn=deploy_with_metadata,
                inputs=[server_name, code, packages, description, category, tags, author, version],
                outputs=deploy_output,
                api_visibility="private"  # Don't expose UI handler as MCP tool
            )

        # Deployments Table Section
        gr.Markdown("### 📋 Active Deployments")

        with gr.Row():
            refresh_btn = gr.Button("🔄 Refresh", size="sm", scale=0)
            search_box = gr.Textbox(
                label="Search",
                placeholder="Filter by name...",
                scale=2
            )
            category_filter = gr.Dropdown(
                label="Filter by Category",
                choices=["All Categories"],
                value="All Categories",
                scale=1
            )

        deployments_df = gr.Dataframe(
            headers=["ID", "Name", "Category", "Tags", "Version", "Author", "Status", "Created"],
            datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
            interactive=False,
            wrap=True,
            label="Deployments"
        )

        # Quick Actions Section
        with gr.Accordion("⚡ Quick Actions", open=False):
            with gr.Row():
                deployment_selector = gr.Dropdown(
                    label="Select Deployment",
                    choices=[],
                    interactive=True
                )
                action_selector = gr.Dropdown(
                    label="Action",
                    choices=["View Status", "Delete (confirm required)"],
                    value="View Status",
                    interactive=True
                )
                execute_btn = gr.Button("Execute", variant="secondary")

            action_output = gr.JSON(label="Action Result")

        # Functions
        def load_deployments():
            """Load all deployments into the table"""
            result = list_deployments()
            if result["success"]:
                data = []
                dropdown_choices = []
                categories = set(["All Categories"])

                for dep in result["deployments"]:
                    # Format tags
                    tags_str = ", ".join(dep.get("tags", [])) if dep.get("tags") else "—"

                    data.append([
                        dep.get("deployment_id", "")[:16] + "...",  # Shortened ID
                        dep.get("server_name", "Unknown"),
                        dep.get("category", "Uncategorized"),
                        tags_str,
                        dep.get("version", "1.0.0"),
                        dep.get("author", "Anonymous"),
                        dep.get("status", "unknown"),
                        dep.get("created_at", "")[:10] if dep.get("created_at") else "N/A"  # Date only
                    ])
                    dropdown_choices.append(
                        (dep["server_name"], dep["deployment_id"])
                    )

                    # Collect unique categories
                    if dep.get("category"):
                        categories.add(dep["category"])

                return data, gr.Dropdown(choices=dropdown_choices), gr.Dropdown(choices=sorted(list(categories)))
            return [], gr.Dropdown(choices=[]), gr.Dropdown(choices=["All Categories"])

        def execute_action(deployment_id, action):
            """Execute selected action on deployment"""
            if not deployment_id:
                return {"success": False, "error": "Select a deployment first"}

            if "Delete" in action:
                return delete_deployment(deployment_id=deployment_id, confirm=True)
            elif "View Status" in action:
                return get_deployment_status(deployment_id=deployment_id)

            return {"success": False, "error": "Unknown action"}

        def filter_deployments(search_term, category_val):
            """Filter deployments by search term and category"""
            result = list_deployments()
            if not result["success"]:
                return []

            filtered_data = []
            for dep in result["deployments"]:
                # Check search term
                search_match = (not search_term or
                               search_term.lower() in dep["server_name"].lower() or
                               search_term.lower() in dep["deployment_id"].lower())

                # Check category filter
                category_match = (category_val == "All Categories" or
                                 dep.get("category", "Uncategorized") == category_val)

                if search_match and category_match:
                    tags_str = ", ".join(dep.get("tags", [])) if dep.get("tags") else "—"
                    filtered_data.append([
                        dep.get("deployment_id", "")[:16] + "...",
                        dep.get("server_name", "Unknown"),
                        dep.get("category", "Uncategorized"),
                        tags_str,
                        dep.get("version", "1.0.0"),
                        dep.get("author", "Anonymous"),
                        dep.get("status", "unknown"),
                        dep.get("created_at", "")[:10] if dep.get("created_at") else "N/A"
                    ])
            return filtered_data

        # Wire up events
        refresh_btn.click(
            fn=load_deployments,
            outputs=[deployments_df, deployment_selector, category_filter],
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        search_box.change(
            fn=filter_deployments,
            inputs=[search_box, category_filter],
            outputs=deployments_df,
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        category_filter.change(
            fn=filter_deployments,
            inputs=[search_box, category_filter],
            outputs=deployments_df,
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        execute_btn.click(
            fn=execute_action,
            inputs=[deployment_selector, action_selector],
            outputs=action_output,
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        # Load deployments on panel load
        panel.load(
            fn=load_deployments,
            outputs=[deployments_df, deployment_selector, category_filter],
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

    return panel
