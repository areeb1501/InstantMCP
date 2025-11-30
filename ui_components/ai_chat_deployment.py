"""
AI Chat Interface for MCP Deployment (Enhanced with Tool Use)

Provides a conversational interface for creating, modifying, and debugging MCP servers.
The AI assistant can now actually deploy and manage servers using tools.
"""

import gradio as gr
import json
import os
from typing import List, Dict, Tuple, Optional
from mcp_tools.ai_assistant import MCPAssistant, validate_api_key, validate_sambanova_env
from mcp_tools.deployment_tools import (
    deploy_mcp_server,
    list_deployments,
    get_deployment_code,
    update_deployment_code,
)


def create_ai_chat_deployment():
    """
    Create the AI-powered chat interface for MCP deployment.

    The AI assistant now has access to actual deployment tools and can:
    - Deploy new MCP servers
    - List existing deployments
    - Get and modify deployment code
    - Check deployment status
    - View usage statistics

    Returns:
        gr.Blocks: AI chat interface
    """
    with gr.Blocks() as chat_interface:
        gr.Markdown("## 🤖 AI-Powered MCP Creation & Management")
        gr.Markdown("""
        Chat with Claude to create, modify, or debug MCP servers.
        
        **🔧 The AI assistant has full access to deployment tools and can actually:**
        - ✅ Deploy new MCP servers to Modal.com
        - ✅ List and check your existing deployments
        - ✅ View and modify deployment code
        - ✅ Update and redeploy servers
        - ✅ Scan code for security vulnerabilities
        - ✅ View usage statistics
        
        Just describe what you want to do!
        """)

        # Session state
        session_state = gr.State({
            "api_key": None,
            "assistant": None,
            "mode": "create",
            "generated_code": None,
            "generated_packages": [],
            "suggested_category": "Uncategorized",
            "suggested_tags": [],
            # Deployment context (pre-loaded when selecting in modify mode)
            "selected_deployment_id": None,
            "selected_deployment_code": None,
            "selected_deployment_metadata": None,
        })

        with gr.Row():
            # Left column: Chat interface
            with gr.Column(scale=2):
                # Model Selection
                model_selector = gr.Dropdown(
                    choices=[
                        ("Claude Sonnet 4 (Anthropic)", "anthropic:claude-sonnet-4-20250514"),
                        ("Meta Llama 3.3 70B (SambaNova)", "sambanova:Meta-Llama-3.3-70B-Instruct"),
                        ("DeepSeek V3 (SambaNova)", "sambanova:DeepSeek-V3-0324"),
                        ("Llama 4 Maverick 17B (SambaNova)", "sambanova:Llama-4-Maverick-17B-128E-Instruct"),
                        ("Qwen3 32B (SambaNova)", "sambanova:Qwen3-32B"),
                        ("GPT OSS 120B (SambaNova)", "sambanova:gpt-oss-120b"),
                        ("DeepSeek V3.1 (SambaNova)", "sambanova:DeepSeek-V3.1"),
                    ],
                    value="anthropic:claude-sonnet-4-20250514",
                    label="🤖 AI Model",
                    info="Select which AI model to use for assistance"
                )

                # API Key input (conditionally visible for Anthropic)
                with gr.Row(visible=True) as api_key_row:
                    api_key_input = gr.Textbox(
                        label="Anthropic API Key",
                        type="password",
                        placeholder="sk-ant-...",
                        scale=3
                    )
                    validate_btn = gr.Button("✓ Validate", size="sm", scale=1, visible=True)

                api_status = gr.Markdown("*API key not set*")

                # Mode selection with enhanced options
                mode_selector = gr.Radio(
                    choices=[
                        ("🚀 Create New MCP", "create"),
                        ("✏️ Modify Existing MCP", "modify"),
                        ("🔍 Debug & Troubleshoot", "debug"),
                        ("📊 View Stats & Status", "stats"),
                    ],
                    value="create",
                    label="Mode",
                    interactive=True
                )

                # Deployment selector (only for modify mode)
                deployment_selector = gr.Dropdown(
                    label="Select Deployment to Modify",
                    choices=[],
                    visible=False,
                    interactive=True
                )
                refresh_deployments_btn = gr.Button(
                    "🔄 Refresh",
                    visible=False,
                    size="sm"
                )

                # Chat interface
                chatbot = gr.Chatbot(
                    label="Chat with Claude (Tool-Use Enabled)",
                    height=500,
                    avatar_images=(
                        None,
                        "https://www.anthropic.com/_next/image?url=%2Fimages%2Ficons%2Ffeature-prompt.svg&w=96&q=75",
                    )
                )

                # Input box
                with gr.Row():
                    msg_input = gr.Textbox(
                        label="Your Message",
                        placeholder="Describe what you want to do... (e.g., 'Create an MCP that fetches weather data' or 'Show me my deployments')",
                        scale=4,
                        lines=2
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)

                # Quick examples organized by mode
                with gr.Accordion("💡 Example Prompts", open=False):
                    gr.Markdown("### Create Mode")
                    gr.Examples(
                        examples=[
                            "Create an MCP that fetches weather data using wttr.in API",
                            "Build an MCP server that converts currencies using an exchange rate API",
                            "Make an MCP tool that searches books using the Open Library API",
                            "Create an MCP with two tools: one to get random cat facts and one to get dog facts",
                        ],
                        inputs=msg_input,
                        label="Creation Examples"
                    )
                    
                    gr.Markdown("### Manage Mode")
                    gr.Examples(
                        examples=[
                            "Show me all my deployed MCP servers",
                            "What's the status of my weather-api deployment?",
                            "Get the code for my cat-facts deployment",
                            "Show me usage statistics for all my deployments",
                        ],
                        inputs=msg_input,
                        label="Management Examples"
                    )
                    
                    gr.Markdown("### Modify Mode")
                    gr.Examples(
                        examples=[
                            "Add error handling to my existing weather MCP",
                            "Add a new tool to my cat-facts server that returns multiple facts",
                            "Update my deployment to add rate limiting",
                            "Fix the security issues in my code",
                        ],
                        inputs=msg_input,
                        label="Modification Examples"
                    )

            # Right column: Code preview and info
            with gr.Column(scale=1):
                gr.Markdown("### 📝 Generated Code Preview")
                gr.Markdown("*Code extracted from AI response will appear here*")

                # Code preview
                code_preview = gr.Code(
                    language="python",
                    label="",
                    lines=20,
                    interactive=True,
                    value="# Code will appear here after chatting with Claude\n# The AI can also deploy directly using tools!"
                )

                # Metadata inputs for manual deployment
                with gr.Accordion("Manual Deployment Options", open=False):
                    gr.Markdown("*Use these only if you want to deploy code manually without asking the AI*")
                    
                    server_name_input = gr.Textbox(
                        label="Server Name",
                        placeholder="e.g., my-weather-api"
                    )
                    category_input = gr.Textbox(
                        label="Category",
                        placeholder="e.g., Weather, Finance, Utilities",
                        value="Uncategorized"
                    )
                    tags_input = gr.Textbox(
                        label="Tags (comma-separated)",
                        placeholder="e.g., api, weather, data"
                    )
                    author_input = gr.Textbox(
                        label="Author",
                        value="Anonymous"
                    )
                    packages_input = gr.Textbox(
                        label="Required Packages (comma-separated)",
                        placeholder="e.g., requests, beautifulsoup4"
                    )

                    # Manual deploy button
                    manual_deploy_btn = gr.Button(
                        "🚀 Manual Deploy",
                        variant="secondary",
                    )

                # Deployment result
                with gr.Accordion("Deployment Results", open=True):
                    deployment_result = gr.JSON(label="Latest Result")

        # Functions

        def validate_or_create_assistant(model_choice: str, api_key: str = None) -> Tuple[str, dict]:
            """Validate API key or create assistant based on model selection"""
            if not model_choice:
                return "❌ *Please select a model*", {"api_key": None, "assistant": None}

            # Parse provider and model from selection
            provider, model = model_choice.split(":")

            if provider == "anthropic":
                # Anthropic requires API key validation
                if not api_key:
                    return "❌ *Please enter an Anthropic API key*", {"api_key": None, "assistant": None}

                if validate_api_key(api_key):
                    try:
                        assistant = MCPAssistant(provider="anthropic", model=model, api_key=api_key)
                        return f"✅ *Ready with {model}!*", {"api_key": api_key, "assistant": assistant}
                    except Exception as e:
                        return f"❌ *Error: {str(e)}*", {"api_key": None, "assistant": None}
                else:
                    return "❌ *Invalid Anthropic API key*", {"api_key": None, "assistant": None}

            elif provider == "sambanova":
                # SambaNova uses environment variable
                is_valid, message = validate_sambanova_env()
                if not is_valid:
                    return f"❌ *{message}*", {"api_key": None, "assistant": None}

                try:
                    assistant = MCPAssistant(provider="sambanova", model=model)
                    return f"✅ *Ready with {model}!*", {"api_key": None, "assistant": assistant}
                except Exception as e:
                    return f"❌ *Error: {str(e)}*", {"api_key": None, "assistant": None}

            else:
                return f"❌ *Unknown provider: {provider}*", {"api_key": None, "assistant": None}

        def update_api_key_visibility(model_choice: str, current_state: dict):
            """Show/hide API key input based on selected model and auto-create SambaNova assistant"""
            if not model_choice:
                return gr.Row(visible=True), "*Please select a model*", current_state

            provider = model_choice.split(":")[0]

            if provider == "anthropic":
                # Clear assistant if switching to Anthropic (requires new API key)
                new_state = {**current_state, "assistant": None, "api_key": None}
                return (
                    gr.Row(visible=True),  # api_key_row
                    "*Enter your Anthropic API key*",  # api_status
                    new_state  # session_state
                )

            elif provider == "sambanova":
                # Auto-create SambaNova assistant
                is_valid, message = validate_sambanova_env()
                if is_valid:
                    try:
                        model = model_choice.split(":")[1]
                        assistant = MCPAssistant(provider="sambanova", model=model)
                        new_state = {**current_state, "assistant": assistant, "api_key": None}
                        return (
                            gr.Row(visible=False),  # api_key_row - hide for SambaNova
                            f"✅ *Ready with {model}!*",  # api_status
                            new_state  # session_state
                        )
                    except Exception as e:
                        new_state = {**current_state, "assistant": None, "api_key": None}
                        return (
                            gr.Row(visible=False),  # api_key_row
                            f"❌ *Error: {str(e)}*",  # api_status
                            new_state  # session_state
                        )
                else:
                    new_state = {**current_state, "assistant": None, "api_key": None}
                    return (
                        gr.Row(visible=False),  # api_key_row
                        f"❌ *{message}*",  # api_status
                        new_state  # session_state
                    )
            else:
                return (
                    gr.Row(visible=True),  # api_key_row
                    "*Unknown provider*",  # api_status
                    current_state  # session_state
                )

        def load_deployment_choices():
            """Load available deployments for the dropdown"""
            try:
                result = list_deployments()

                # Debug: Print result for troubleshooting
                print(f"[DEBUG] list_deployments result: success={result.get('success')}, total={result.get('total', 0)}")

                if result.get("success"):
                    deployments = result.get("deployments", [])

                    if not deployments:
                        print("[DEBUG] No deployments found in database")
                        return []

                    choices = []
                    for dep in deployments:
                        # Build a descriptive label
                        server_name = dep.get("server_name", "Unknown")
                        app_name = dep.get("app_name", "")
                        deployment_id = dep.get("deployment_id", "")

                        if not deployment_id:
                            print(f"[DEBUG] Skipping deployment without ID: {dep}")
                            continue

                        label = f"{server_name}"
                        if app_name:
                            label += f" ({app_name})"

                        choices.append((label, deployment_id))

                    print(f"[DEBUG] Loaded {len(choices)} deployment choices")
                    return choices
                else:
                    error = result.get("error", "Unknown error")
                    print(f"[DEBUG] list_deployments failed: {error}")
                    return []

            except Exception as e:
                print(f"[ERROR] Exception loading deployments: {e}")
                import traceback
                traceback.print_exc()
                return []

        def update_mode_visibility(mode: str):
            """Update UI based on selected mode"""
            show_deployment_selector = mode == "modify"

            print(f"[DEBUG] Mode changed to: {mode}, show_dropdown: {show_deployment_selector}")

            # Load deployments if in modify mode
            if show_deployment_selector:
                choices = load_deployment_choices()
                print(f"[DEBUG] Found {len(choices)} choices for dropdown")

                if choices:
                    return (
                        gr.update(
                            choices=choices,
                            visible=True,
                            value=None,
                            interactive=True,
                            label="Select Deployment to Modify",
                            info=None
                        ),
                        gr.update(visible=True)
                    )
                else:
                    return (
                        gr.update(
                            choices=[],
                            visible=True,
                            value=None,
                            interactive=True,
                            label="Select Deployment to Modify",
                            info="⚠️ No deployments found. Create one first!"
                        ),
                        gr.update(visible=True)
                    )

            # Hide both when not in modify mode
            print("[DEBUG] Hiding dropdown and button")
            return (
                gr.update(visible=False),
                gr.update(visible=False)
            )

        def refresh_deployments():
            """Refresh the deployment list"""
            print("[DEBUG] Refreshing deployment list...")
            choices = load_deployment_choices()
            print(f"[DEBUG] Refresh found {len(choices)} deployments")

            if choices:
                return gr.update(
                    choices=choices,
                    value=None,
                    visible=True,
                    interactive=True,
                    label="Select Deployment to Modify",
                    info=None
                )
            else:
                return gr.update(
                    choices=[],
                    value=None,
                    visible=True,
                    interactive=True,
                    label="Select Deployment to Modify",
                    info="⚠️ No deployments found. Create one first!"
                )

        def load_deployment_context(deployment_id: Optional[str], state: dict, history: List[Dict]):
            """
            Load deployment context when a deployment is selected.

            This fetches the deployment code and metadata, injects it into the session state,
            and adds a context message to the chat so the AI has immediate access.

            Args:
                deployment_id: Selected deployment ID
                state: Current session state
                history: Current chat history

            Returns:
                Tuple of (updated_history, updated_state, code_preview)
            """
            if not deployment_id:
                # Clear context if no deployment selected
                new_state = {
                    **state,
                    "selected_deployment_id": None,
                    "selected_deployment_code": None,
                    "selected_deployment_metadata": None,
                }
                return history, new_state, "# No deployment selected"

            print(f"[DEBUG] Loading context for deployment: {deployment_id}")

            try:
                # Fetch deployment code and status
                code_result = get_deployment_code(deployment_id)

                if not code_result.get("success"):
                    error_msg = code_result.get("error", "Unknown error")
                    new_history = [
                        *history,
                        {
                            "role": "assistant",
                            "content": f"❌ Failed to load deployment: {error_msg}"
                        }
                    ]
                    return new_history, state, f"# Error loading deployment\n# {error_msg}"

                # Extract deployment info (data is directly in code_result, not nested)
                server_name = code_result.get("server_name", "Unknown")
                mcp_code = code_result.get("code", "")
                packages_list = code_result.get("packages", [])
                packages = ", ".join(packages_list) if packages_list else ""
                description = code_result.get("description", "")
                url = code_result.get("url", "")

                # Get app name from deployment_id (format: deploy-mcp-<name>-<hash>)
                app_name = deployment_id.replace("deploy-", "") if deployment_id.startswith("deploy-") else deployment_id

                # Update state with deployment context
                new_state = {
                    **state,
                    "selected_deployment_id": deployment_id,
                    "selected_deployment_code": mcp_code,
                    "selected_deployment_metadata": {
                        "server_name": server_name,
                        "app_name": app_name,
                        "packages": packages,
                        "description": description,
                        "url": url,
                        "deployment_id": deployment_id,
                    }
                }

                # Add context message to chat
                context_message = f"""✅ **Loaded: {server_name}**

**Deployment ID:** `{deployment_id}`
**App Name:** `{app_name}`
**URL:** {url}
**Packages:** {packages if packages else "None"}

The current code for this deployment is now loaded in the code preview.
You can now ask me to modify, enhance, or debug this MCP server!

**Example prompts:**
- "Add error handling to all functions"
- "Add a new tool that does X"
- "Fix the security issues"
- "Add rate limiting"
"""

                new_history = [
                    *history,
                    {
                        "role": "assistant",
                        "content": context_message
                    }
                ]

                print(f"[DEBUG] Successfully loaded deployment context for {server_name}")

                return new_history, new_state, mcp_code

            except Exception as e:
                print(f"[ERROR] Exception loading deployment context: {e}")
                import traceback
                traceback.print_exc()

                error_history = [
                    *history,
                    {
                        "role": "assistant",
                        "content": f"❌ Error loading deployment: {str(e)}"
                    }
                ]
                return error_history, state, f"# Error\n# {str(e)}"

        def chat_response(
            message: str,
            history: List[Dict],
            state: dict,
            mode: str,
            deployment_id: Optional[str] = None
        ):
            """
            Handle chat messages and generate responses with tool execution.

            The AI assistant now uses tools to actually perform operations,
            not just generate code.

            Streams responses in real-time using yield.
            """

            # Check if API key is set
            if not state.get("assistant"):
                error_msg = [
                    *history,
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": "❌ Please set and validate your API key first."}
                ]
                yield (
                    error_msg,
                    state,
                    code_preview.value,
                    None
                )
                return

            assistant = state["assistant"]

            # Add user message to history
            history = history or []
            history.append({"role": "user", "content": message})

            # Immediately show user message
            yield (
                history,
                state,
                code_preview.value,
                None
            )

            # Build context based on mode and pre-loaded deployment data
            context_message = message

            if mode == "modify" and state.get("selected_deployment_metadata"):
                # Use pre-loaded deployment context (much more efficient!)
                metadata = state["selected_deployment_metadata"]
                current_code = state.get("selected_deployment_code", "")

                context_message = f"""[DEPLOYMENT CONTEXT - Pre-loaded for efficiency]
Deployment ID: {metadata['deployment_id']}
Server Name: {metadata['server_name']}
App Name: {metadata['app_name']}
Current Packages: {metadata['packages']}
URL: {metadata['url']}

CURRENT CODE:
```python
{current_code}
```

USER REQUEST: {message}

NOTE: The deployment code is already loaded above. You can directly suggest modifications without calling get_deployment_code. When you're ready to update, use the update_deployment_code tool with deployment_id='{metadata['deployment_id']}'.
"""
            elif mode == "stats":
                context_message = f"[Context: User wants to view statistics or status]\n\n{message}"
            elif mode == "debug":
                context_message = f"[Context: User is debugging/troubleshooting]\n\n{message}"

            # Add empty assistant message that we'll stream into
            history.append({"role": "assistant", "content": ""})

            # Stream response with tool execution
            response_text = ""
            try:
                for chunk in assistant.chat_stream(context_message, history[:-2]):
                    response_text += chunk
                    # Update the last message (assistant's response) with accumulated text
                    history[-1] = {"role": "assistant", "content": response_text}

                    # Yield updated history to show streaming in real-time
                    yield (
                        history,
                        state,
                        code_preview.value,
                        None
                    )

            except Exception as e:
                response_text = f"❌ Error: {str(e)}"
                history[-1] = {"role": "assistant", "content": response_text}
                yield (
                    history,
                    state,
                    code_preview.value,
                    None
                )
                return

            # Try to parse code from response for preview
            parsed = assistant._parse_response(response_text)

            # Update state and code preview
            new_state = {**state}
            new_code = code_preview.value

            if parsed["code"]:
                new_state["generated_code"] = parsed["code"]
                new_state["generated_packages"] = parsed["packages"]
                new_state["suggested_category"] = parsed["category"]
                new_state["suggested_tags"] = parsed["tags"]
                new_code = parsed["code"]

            # Extract any deployment results from response
            deployment_info = None
            if "URL:" in response_text and "modal.run" in response_text:
                # Try to extract URL for display
                import re
                url_match = re.search(r'https://[a-zA-Z0-9-]+--[a-zA-Z0-9-]+\.modal\.run', response_text)
                if url_match:
                    deployment_info = {
                        "success": True,
                        "url": url_match.group(0),
                        "mcp_endpoint": url_match.group(0) + "/mcp/",
                        "message": "Deployment URL extracted from response"
                    }

            # Final yield with all updates (code preview, deployment info)
            yield (
                history,
                new_state,
                new_code,
                deployment_info
            )

        def manual_deploy(
            code: str,
            server_name: str,
            category: str,
            tags: str,
            author: str,
            packages: str,
        ):
            """Manually deploy code without AI assistance"""

            if not code or code.startswith("#"):
                return {"success": False, "error": "No code to deploy"}

            if not server_name:
                return {"success": False, "error": "Server name is required"}

            # Parse tags and packages
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
            packages_str = packages.strip()

            try:
                result = deploy_mcp_server(
                    server_name=server_name,
                    mcp_tools_code=code,
                    extra_pip_packages=packages_str,
                    description=f"Manually deployed - {category}",
                    category=category,
                    tags=tags_list,
                    author=author,
                )
                return result

            except Exception as e:
                return {"success": False, "error": str(e)}

        # Event handlers
        # NOTE: All UI event handlers use api_visibility="private" to prevent exposure via MCP endpoint (Gradio 6.x)

        # Update API key visibility when model changes (auto-create SambaNova assistant)
        model_selector.change(
            fn=update_api_key_visibility,
            inputs=[model_selector, session_state],
            outputs=[api_key_row, api_status, session_state],
            api_visibility="private"  # Prevent exposure as MCP tool
        )

        # Validate API key or create assistant
        validate_btn.click(
            fn=validate_or_create_assistant,
            inputs=[model_selector, api_key_input],
            outputs=[api_status, session_state],
            api_visibility="private"  # Prevent exposure as MCP tool
        )

        mode_selector.change(
            fn=update_mode_visibility,
            inputs=[mode_selector],
            outputs=[deployment_selector, refresh_deployments_btn],
            api_visibility="private"  # Prevent exposure as MCP tool
        )

        # Refresh deployments button
        refresh_deployments_btn.click(
            fn=refresh_deployments,
            outputs=[deployment_selector],
            api_visibility="private"  # Prevent exposure as MCP tool
        )

        # Load deployment context when a deployment is selected
        deployment_selector.change(
            fn=load_deployment_context,
            inputs=[deployment_selector, session_state, chatbot],
            outputs=[chatbot, session_state, code_preview],
            api_visibility="private"  # Prevent exposure as MCP tool
        )

        # Send message on button click
        send_btn.click(
            fn=chat_response,
            inputs=[msg_input, chatbot, session_state, mode_selector, deployment_selector],
            outputs=[
                chatbot,
                session_state,
                code_preview,
                deployment_result
            ],
            api_visibility="private"  # Prevent exposure as MCP tool
        ).then(
            fn=lambda: "",  # Clear input
            outputs=[msg_input],
            api_visibility="private"  # Prevent exposure as MCP tool
        )

        # Send message on Enter
        msg_input.submit(
            fn=chat_response,
            inputs=[msg_input, chatbot, session_state, mode_selector, deployment_selector],
            outputs=[
                chatbot,
                session_state,
                code_preview,
                deployment_result
            ],
            api_visibility="private"  # Prevent exposure as MCP tool
        ).then(
            fn=lambda: "",
            outputs=[msg_input],
            api_visibility="private"  # Prevent exposure as MCP tool
        )

        # Manual deploy button
        manual_deploy_btn.click(
            fn=manual_deploy,
            inputs=[
                code_preview,
                server_name_input,
                category_input,
                tags_input,
                author_input,
                packages_input,
            ],
            outputs=[deployment_result],
            api_visibility="private"  # Prevent exposure as MCP tool
        )

        # Initialize interface on load
        def initialize_interface(mode: str, model: str, state: dict):
            """
            Initialize the interface when page loads.

            This pre-loads deployment choices so they're ready immediately
            when switching to modify mode.
            """
            # Pre-load deployment choices
            choices = load_deployment_choices()
            print(f"[DEBUG] Page load: Preloaded {len(choices)} deployment choices")

            # Update dropdown with choices (keep it hidden for now since mode is "create" by default)
            dropdown_update = gr.update(
                choices=choices,
                visible=False  # Will be shown when mode changes to "modify"
            )

            # Get API key visibility
            api_key_row_update, api_status_text, new_state = update_api_key_visibility(model, state)

            return (
                dropdown_update,  # deployment_selector
                gr.update(visible=False),  # refresh_deployments_btn
                api_key_row_update,  # api_key_row
                api_status_text,  # api_status
                new_state  # session_state
            )

        # Single load event that initializes everything
        chat_interface.load(
            fn=initialize_interface,
            inputs=[mode_selector, model_selector, session_state],
            outputs=[deployment_selector, refresh_deployments_btn, api_key_row, api_status, session_state],
            api_visibility="private"  # Prevent exposure as MCP tool
        )

    return chat_interface