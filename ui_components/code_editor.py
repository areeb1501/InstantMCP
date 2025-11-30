"""
Code Editor UI Component

Interactive code editor for MCP tool development.

FIXES APPLIED:
- Added try/except error handling in load_code()
- Using .get() with defaults for ALL fields to prevent KeyError
- Better error messages and fallbacks
- Handles missing url, description, and other fields gracefully
"""

import gradio as gr
from mcp_tools.deployment_tools import (
    get_deployment_code,
    list_deployments,
    update_deployment_code,
)


def create_code_editor():
    """
    Create the code editor UI component.

    Returns:
        gr.Blocks: Code editor interface
    """
    with gr.Blocks() as editor:
        gr.Markdown("## 💻 Code Editor")
        gr.Markdown("Edit and view your deployment code inline")

        # Load Deployment Section
        with gr.Row():
            deployment_selector = gr.Dropdown(
                label="Select Deployment",
                choices=[],
                interactive=True,
                scale=3
            )
            load_btn = gr.Button("📥 Load Code", size="sm", scale=1)
            refresh_deployments_btn = gr.Button("🔄", size="sm", scale=0)

        # Deployment Info Display
        with gr.Row():
            with gr.Column(scale=1):
                deployment_info = gr.Markdown("*Select a deployment to view details*")
            with gr.Column(scale=1):
                packages_display = gr.Textbox(
                    label="Current Packages",
                    interactive=True,  # Allow editing packages
                    placeholder="No deployment loaded"
                )

        # Code Editor Section
        gr.Markdown("### 📝 MCP Tools Code")
        code_editor = gr.Code(
            language="python",
            label="",
            lines=20,
            interactive=True,
            value="# Load a deployment to view and edit code"
        )

        # Tools Preview
        tools_preview = gr.JSON(
            label="📋 Detected Tools",
            value={}
        )

        # Action Buttons
        with gr.Row():
            save_btn = gr.Button("💾 Save & Redeploy", variant="primary", interactive=True)
            preview_btn = gr.Button("👁️ Preview", variant="secondary")
            deploy_btn = gr.Button("🚀 Deploy as New (Coming Soon)", interactive=False)

        # Output/Result Display
        output = gr.JSON(label="Result")

        # Functions
        def load_deployment_list():
            """Load list of deployments for dropdown"""
            try:
                result = list_deployments()
                if result.get("success"):
                    choices = [
                        (dep.get("server_name", "Unknown"), dep.get("deployment_id", ""))
                        for dep in result.get("deployments", [])
                        if dep.get("deployment_id")  # Only include if we have an ID
                    ]
                    return gr.update(choices=choices)
                return gr.update(choices=[])
            except Exception as e:
                print(f"Error loading deployment list: {e}")
                return gr.update(choices=[])

        def load_code(deployment_id):
            """
            Load code for selected deployment.
            
            ✅ FIXED: Now uses .get() with defaults for ALL fields
            ✅ FIXED: Wrapped in try/except for error handling
            """
            # Handle empty selection
            if not deployment_id:
                return (
                    "# Select a deployment first",
                    "*No deployment selected*",
                    "",
                    {},
                    {"success": False, "error": "No deployment selected"}
                )

            try:
                result = get_deployment_code(deployment_id)

                if result.get("success"):
                    # ✅ FIX: Use .get() with defaults for ALL fields to prevent KeyError
                    deployment_id_val = result.get('deployment_id', 'N/A')
                    server_name = result.get('server_name', 'Unknown')
                    description = result.get('description', 'No description')
                    url = result.get('url', '')
                    mcp_endpoint = result.get('mcp_endpoint', '')
                    status = result.get('status', 'unknown')
                    category = result.get('category', 'Uncategorized')
                    author = result.get('author', 'Anonymous')
                    version = result.get('version', '1.0.0')
                    tools = result.get('tools', [])
                    packages = result.get('packages', [])
                    code = result.get('code', '# No code available')
                    created_at = result.get('created_at', 'Unknown')

                    # Format deployment info markdown
                    # ✅ FIX: Handle empty/None URL gracefully
                    if url:
                        url_display = f"[{url}]({url})"
                    else:
                        url_display = "*Not available*"
                    
                    if mcp_endpoint:
                        mcp_display = f"`{mcp_endpoint}`"
                    else:
                        mcp_display = "*Not available*"

                    info_md = f"""
### 📋 Deployment Details

| Field | Value |
|-------|-------|
| **Deployment ID** | `{deployment_id_val}` |
| **Server Name** | {server_name} |
| **Description** | {description or 'N/A'} |
| **Status** | {status} |
| **Category** | {category} |
| **Author** | {author} |
| **Version** | {version} |
| **Created** | {created_at} |
| **Tools Count** | {len(tools)} detected |

**🔗 URL:** {url_display}

**📡 MCP Endpoint:** {mcp_display}
"""

                    # Format packages string
                    packages_str = ", ".join(packages) if packages else "No extra packages"

                    return (
                        code if code else "# No code available",
                        info_md,
                        packages_str,
                        tools if tools else [],
                        result
                    )
                else:
                    # Handle API error response
                    error_msg = result.get('error', 'Unknown error occurred')
                    return (
                        f"# Error loading code\n# {error_msg}",
                        f"### ❌ Error\n\n{error_msg}",
                        "",
                        {},
                        result
                    )

            except Exception as e:
                # ✅ FIX: Catch any unexpected exceptions
                error_msg = str(e)
                return (
                    f"# Exception occurred while loading code\n# {error_msg}",
                    f"### ❌ Exception\n\n```\n{error_msg}\n```\n\nPlease try refreshing the deployment list.",
                    "",
                    {},
                    {"success": False, "error": error_msg, "exception": True}
                )

        def preview_code(code):
            """Preview code analysis"""
            if not code or code.startswith("#"):
                return {"info": "Enter code to preview"}

            try:
                # Basic code analysis
                lines = code.split('\n')
                tool_count = sum(1 for line in lines if '@mcp.tool()' in line)
                import_count = sum(1 for line in lines if line.strip().startswith(('import ', 'from ')))
                
                # Check for required components
                has_fastmcp_import = 'from fastmcp import FastMCP' in code or 'import FastMCP' in code
                has_mcp_instance = 'mcp = FastMCP(' in code
                has_tools = tool_count > 0

                # Validation status
                is_valid = has_fastmcp_import and has_mcp_instance and has_tools
                
                validation_issues = []
                if not has_fastmcp_import:
                    validation_issues.append("Missing: from fastmcp import FastMCP")
                if not has_mcp_instance:
                    validation_issues.append("Missing: mcp = FastMCP('server-name')")
                if not has_tools:
                    validation_issues.append("Missing: @mcp.tool() decorated functions")

                return {
                    "total_lines": len(lines),
                    "detected_tools": tool_count,
                    "imports": import_count,
                    "is_valid": is_valid,
                    "validation_issues": validation_issues if validation_issues else ["✅ All checks passed"],
                    "preview": "Code analysis complete"
                }
            except Exception as e:
                return {
                    "error": str(e),
                    "preview": "Code analysis failed"
                }

        def save_and_redeploy(deployment_id, edited_code, packages_str):
            """Save edited code and redeploy to Modal"""
            # Validate deployment selection
            if not deployment_id:
                return {"success": False, "error": "No deployment selected"}

            # Validate code
            if not edited_code:
                return {"success": False, "error": "No code provided"}
            
            if edited_code.startswith("# Load") or edited_code.startswith("# Error") or edited_code.startswith("# Select"):
                return {"success": False, "error": "No valid code to save. Please load a deployment first."}

            if edited_code.startswith("# Exception"):
                return {"success": False, "error": "Cannot save error placeholder. Please load a valid deployment."}

            try:
                # Convert packages string to list
                package_list = []
                if packages_str and not packages_str.startswith("No"):
                    package_list = [p.strip() for p in packages_str.split(",") if p.strip()]

                # Call update function
                result = update_deployment_code(
                    deployment_id=deployment_id,
                    mcp_tools_code=edited_code,
                    extra_pip_packages=package_list
                )

                return result
                
            except Exception as e:
                return {
                    "success": False, 
                    "error": f"Exception during save: {str(e)}",
                    "exception": True
                }

        # Wire up events
        refresh_deployments_btn.click(
            fn=load_deployment_list,
            outputs=deployment_selector,
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        load_btn.click(
            fn=load_code,
            inputs=[deployment_selector],
            outputs=[code_editor, deployment_info, packages_display, tools_preview, output],
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        save_btn.click(
            fn=save_and_redeploy,
            inputs=[deployment_selector, code_editor, packages_display],
            outputs=output,
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        preview_btn.click(
            fn=preview_code,
            inputs=[code_editor],
            outputs=output,
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

        # Load deployments on editor load
        editor.load(
            fn=load_deployment_list,
            outputs=deployment_selector,
            api_visibility="private"  # Don't expose UI handler as MCP tool
        )

    return editor
