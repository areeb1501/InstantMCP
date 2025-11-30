"""
AI Assistant Helper Module (Enhanced with Tool Use)

Handles Claude API interactions for MCP code generation, modification, and debugging.
Now includes tool-use capability to actually deploy, manage, and interact with MCP servers.
"""

import json
import os
from typing import List, Dict, Optional, Generator, Any, Callable
from anthropic import Anthropic
import openai

# Import MCP deployment tools for tool execution
from mcp_tools.deployment_tools import (
    deploy_mcp_server,
    list_deployments,
    get_deployment_status,
    delete_deployment,
    get_deployment_code,
    update_deployment_code,
)
from mcp_tools.stats_tools import (
    get_deployment_stats,
    get_tool_usage,
    get_all_stats_summary,
)
from mcp_tools.security_tools import scan_deployment_security


# =============================================================================
# TOOL DEFINITIONS FOR CLAUDE
# =============================================================================
# These match the MCP tools available in the platform

TOOL_DEFINITIONS = [
    {
        "name": "deploy_mcp_server",
        "description": """Deploy an MCP server with custom tools to Modal.com.

The deployed server will:
- Use minimal CPU (0.25 cores) and memory (256MB)
- Scale to zero when not in use (no billing when idle)
- Allow cold starts (2-5 second startup time)
- Be accessible via a public URL

IMPORTANT CODE FORMAT REQUIREMENTS:
Your mcp_tools_code MUST include:
✅ `from fastmcp import FastMCP` import
✅ `mcp = FastMCP("server-name")` initialization
✅ One or more `@mcp.tool()` decorated functions
✅ Docstrings for each tool (used as descriptions)
✅ Type hints for parameters and return values

❌ DO NOT include:
❌ `mcp.run()` or any server startup code
❌ `if __name__ == "__main__"` blocks
❌ Modal-specific imports or setup

Example code:
```python
from fastmcp import FastMCP

mcp = FastMCP("cat-facts")

@mcp.tool()
def get_cat_fact() -> str:
    '''Get a random cat fact from an API'''
    import requests
    response = requests.get("https://catfact.ninja/fact")
    return response.json()["fact"]
```""",
        "input_schema": {
            "type": "object",
            "properties": {
                "server_name": {
                    "type": "string",
                    "description": "Unique name for your MCP server (e.g., 'weather-api', 'cat-facts')"
                },
                "mcp_tools_code": {
                    "type": "string",
                    "description": "Complete MCP server code as a string with FastMCP import, initialization, and @mcp.tool() decorated functions"
                },
                "extra_pip_packages": {
                    "type": "string",
                    "description": "Comma-separated list of PyPI packages (e.g., 'requests,pandas')"
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what the server does"
                },
                "category": {
                    "type": "string",
                    "description": "Category for organizing (e.g., 'Weather', 'Finance', 'Utilities')"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags for filtering and search"
                },
                "author": {
                    "type": "string",
                    "description": "Author name"
                },
                "version": {
                    "type": "string",
                    "description": "Semantic version (e.g., '1.0.0')"
                }
            },
            "required": ["server_name", "mcp_tools_code"]
        }
    },
    {
        "name": "list_deployments",
        "description": "List all deployed MCP servers with their details including URLs, status, and usage statistics.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_deployment_status",
        "description": "Get detailed status of a deployed MCP server including live status check.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment_id": {
                    "type": "string",
                    "description": "The deployment ID (e.g., 'deploy-mcp-weather-abc123')"
                },
                "app_name": {
                    "type": "string",
                    "description": "Or the Modal app name"
                }
            },
            "required": []
        }
    },
    {
        "name": "delete_deployment",
        "description": "Delete a deployed MCP server from Modal. Requires confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment_id": {
                    "type": "string",
                    "description": "The deployment ID to delete"
                },
                "app_name": {
                    "type": "string",
                    "description": "Or the Modal app name to delete"
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to confirm deletion"
                }
            },
            "required": ["confirm"]
        }
    },
    {
        "name": "get_deployment_code",
        "description": "Get the current MCP tools code for a deployment. Use this to view existing code before modifying it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment_id": {
                    "type": "string",
                    "description": "The deployment ID"
                }
            },
            "required": ["deployment_id"]
        }
    },
    {
        "name": "update_deployment_code",
        "description": """Update deployment code and/or packages with redeployment to Modal.

This will redeploy the MCP server with new code/packages while preserving the same URL.
The deployment will experience brief downtime (5-10 seconds) during the update.

Workflow:
1. First use get_deployment_code() to get the current code
2. Make your modifications
3. Use this function to deploy the changes""",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment_id": {
                    "type": "string",
                    "description": "The deployment ID to update"
                },
                "mcp_tools_code": {
                    "type": "string",
                    "description": "New MCP tools code (triggers redeployment)"
                },
                "extra_pip_packages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New package list (triggers redeployment)"
                },
                "server_name": {
                    "type": "string",
                    "description": "New server name"
                },
                "description": {
                    "type": "string",
                    "description": "New description"
                }
            },
            "required": ["deployment_id"]
        }
    },
    {
        "name": "get_deployment_stats",
        "description": "Get usage statistics for a specific deployment including request counts and response times.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment_id": {
                    "type": "string",
                    "description": "The deployment ID to get stats for"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default: 30)"
                }
            },
            "required": ["deployment_id"]
        }
    },
    {
        "name": "get_tool_usage",
        "description": "Get breakdown of tool usage for a deployment - which tools are being called most.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment_id": {
                    "type": "string",
                    "description": "The deployment ID"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default: 30)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of tools to return (default: 10)"
                }
            },
            "required": ["deployment_id"]
        }
    },
    {
        "name": "get_all_stats_summary",
        "description": "Get quick statistics summary for all deployments.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "scan_deployment_security",
        "description": """Manually scan MCP code for security vulnerabilities WITHOUT deploying.

Use this to check code for security issues before deploying. The scan detects:
- Code injection vulnerabilities (SQL, command, etc.)
- Malicious network behavior
- Resource abuse patterns
- Destructive operations
- Known malicious packages""",
        "input_schema": {
            "type": "object",
            "properties": {
                "mcp_tools_code": {
                    "type": "string",
                    "description": "Python code defining your MCP tools"
                },
                "server_name": {
                    "type": "string",
                    "description": "Name for context"
                },
                "extra_pip_packages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional pip packages to check"
                },
                "description": {
                    "type": "string",
                    "description": "Optional description for context"
                }
            },
            "required": ["mcp_tools_code"]
        }
    }
]


# =============================================================================
# TOOL EXECUTION MAPPING
# =============================================================================

def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool by name with given input parameters.
    
    Args:
        tool_name: Name of the tool to execute
        tool_input: Dictionary of input parameters
        
    Returns:
        Tool execution result as a dictionary
    """
    tool_map: Dict[str, Callable] = {
        "deploy_mcp_server": _execute_deploy_mcp_server,
        "list_deployments": _execute_list_deployments,
        "get_deployment_status": _execute_get_deployment_status,
        "delete_deployment": _execute_delete_deployment,
        "get_deployment_code": _execute_get_deployment_code,
        "update_deployment_code": _execute_update_deployment_code,
        "get_deployment_stats": _execute_get_deployment_stats,
        "get_tool_usage": _execute_get_tool_usage,
        "get_all_stats_summary": _execute_get_all_stats_summary,
        "scan_deployment_security": _execute_scan_deployment_security,
    }
    
    if tool_name not in tool_map:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    try:
        return tool_map[tool_name](tool_input)
    except Exception as e:
        return {"success": False, "error": f"Tool execution error: {str(e)}"}


def _execute_deploy_mcp_server(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute deploy_mcp_server with parameters"""
    return deploy_mcp_server(
        server_name=params.get("server_name", ""),
        mcp_tools_code=params.get("mcp_tools_code", ""),
        extra_pip_packages=params.get("extra_pip_packages", ""),
        description=params.get("description", ""),
        category=params.get("category", "Uncategorized"),
        tags=params.get("tags", []),
        author=params.get("author", "AI Assistant"),
        version=params.get("version", "1.0.0"),
    )


def _execute_list_deployments(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute list_deployments"""
    return list_deployments()


def _execute_get_deployment_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute get_deployment_status with parameters"""
    return get_deployment_status(
        deployment_id=params.get("deployment_id", ""),
        app_name=params.get("app_name", ""),
    )


def _execute_delete_deployment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute delete_deployment with parameters"""
    return delete_deployment(
        deployment_id=params.get("deployment_id", ""),
        app_name=params.get("app_name", ""),
        confirm=params.get("confirm", False),
    )


def _execute_get_deployment_code(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute get_deployment_code with parameters"""
    return get_deployment_code(
        deployment_id=params.get("deployment_id", ""),
    )


def _execute_update_deployment_code(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute update_deployment_code with parameters"""
    return update_deployment_code(
        deployment_id=params.get("deployment_id", ""),
        mcp_tools_code=params.get("mcp_tools_code"),
        extra_pip_packages=params.get("extra_pip_packages"),
        server_name=params.get("server_name"),
        description=params.get("description"),
    )


def _execute_get_deployment_stats(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute get_deployment_stats with parameters"""
    return get_deployment_stats(
        deployment_id=params.get("deployment_id", ""),
        days=params.get("days", 30),
    )


def _execute_get_tool_usage(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute get_tool_usage with parameters"""
    return get_tool_usage(
        deployment_id=params.get("deployment_id", ""),
        days=params.get("days", 30),
        limit=params.get("limit", 10),
    )


def _execute_get_all_stats_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute get_all_stats_summary"""
    return get_all_stats_summary()


def _execute_scan_deployment_security(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute scan_deployment_security with parameters"""
    return scan_deployment_security(
        mcp_tools_code=params.get("mcp_tools_code", ""),
        server_name=params.get("server_name", "Unknown"),
        extra_pip_packages=params.get("extra_pip_packages", []),
        description=params.get("description"),
    )


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """You are an MCP server deployment assistant with FULL ACCESS to deployment tools. You can actually deploy, modify, and manage MCP servers - not just generate code.

AVAILABLE TOOLS:
You have access to the following tools that you can call to perform actual operations:

1. **deploy_mcp_server** - Deploy new MCP servers to Modal.com
2. **list_deployments** - List all deployed servers
3. **get_deployment_status** - Check status of a deployment
4. **delete_deployment** - Delete a deployment (requires confirmation)
5. **get_deployment_code** - Get the current code for a deployment
6. **update_deployment_code** - Update code/packages and redeploy
7. **get_deployment_stats** - Get usage statistics
8. **get_tool_usage** - See which tools are being used most
9. **get_all_stats_summary** - Overview of all deployments
10. **scan_deployment_security** - Scan code for vulnerabilities before deploying

WORKFLOW GUIDELINES:

When creating a new MCP server:
1. Understand the user's requirements
2. Generate the MCP code following the correct format
3. Optionally scan for security issues first using scan_deployment_security
4. Call deploy_mcp_server with the code to actually deploy it
5. Report the deployment URL back to the user

When modifying an existing server:
1. Call list_deployments to find the deployment
2. Call get_deployment_code to get the current code
3. Make the requested modifications
4. Call update_deployment_code to deploy the changes
5. Report the results

CODE FORMAT REQUIREMENTS:
When generating MCP code, it MUST include:
✅ `from fastmcp import FastMCP` import
✅ `mcp = FastMCP("server-name")` initialization
✅ One or more `@mcp.tool()` decorated functions
✅ Docstrings for each tool
✅ Type hints for parameters and return values

❌ DO NOT include:
❌ `mcp.run()` or any server startup code
❌ `if __name__ == "__main__"` blocks

EXAMPLE MCP CODE:
```python
from fastmcp import FastMCP
import requests

mcp = FastMCP("weather-api")

@mcp.tool()
def get_weather(city: str) -> dict:
    '''Get current weather for a city.
    
    Args:
        city: Name of the city
        
    Returns:
        Weather data including temperature and conditions
    '''
    try:
        response = requests.get(
            f"https://wttr.in/{city}?format=j1",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        current = data["current_condition"][0]
        return {
            "city": city,
            "temperature_c": current["temp_C"],
            "description": current["weatherDesc"][0]["value"],
            "humidity": current["humidity"]
        }
    except Exception as e:
        return {"error": str(e), "city": city}
```

SECURITY GUIDELINES:
- Always validate and sanitize user inputs
- Use timeouts on HTTP requests
- Never execute arbitrary code from user input
- Use environment variables for API keys: `os.getenv('API_KEY', 'default')`
- Handle exceptions gracefully

IMPORTANT: You can and should USE THE TOOLS to actually perform operations. Don't just show code - deploy it when the user asks!"""


# =============================================================================
# MCP ASSISTANT CLASS WITH TOOL USE
# =============================================================================

class MCPAssistant:
    """Helper class for AI-assisted MCP development with tool-use capability"""

    def __init__(self, provider: str = "anthropic", model: str = None, api_key: Optional[str] = None):
        """
        Initialize the MCP Assistant with support for multiple AI providers.

        Args:
            provider: AI provider ("anthropic" or "sambanova")
            model: Model name (provider-specific)
            api_key: API key (required for Anthropic, ignored for SambaNova which uses env var)
        """
        self.provider = provider.lower()

        if self.provider == "anthropic":
            if not api_key:
                raise ValueError("API key is required for Anthropic provider")
            self.client = Anthropic(api_key=api_key)
            self.model = model or "claude-sonnet-4-20250514"

        elif self.provider == "sambanova":
            sambanova_api_key = os.getenv("SAMBANOVA_API_KEY")
            if not sambanova_api_key:
                raise ValueError("SAMBANOVA_API_KEY not found in environment variables")

            sambanova_base_url = os.getenv("SAMBANOVA_BASE_URL", "https://api.sambanova.ai/v1")

            self.client = openai.OpenAI(
                base_url=sambanova_base_url,
                api_key=sambanova_api_key
            )
            self.model = model or "Meta-Llama-3.3-70B-Instruct"

        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'anthropic' or 'sambanova'")

    def _convert_tools_to_openai_format(self, anthropic_tools: List[Dict]) -> List[Dict]:
        """
        Convert Anthropic tool format to OpenAI tool format.

        Args:
            anthropic_tools: Tools in Anthropic format

        Returns:
            Tools in OpenAI format
        """
        openai_tools = []
        for tool in anthropic_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools

    def chat_stream(
        self,
        message: str,
        history: List[Dict[str, str]] = None,
        max_tokens: int = 4096
    ) -> Generator[str, None, None]:
        """
        Stream chat responses with tool-use support for multiple providers.

        This method handles the full conversation including tool calls.
        When the AI wants to use a tool, it executes the tool and continues
        the conversation with the results.

        Args:
            message: User message
            history: Chat history in Gradio format [{role, content}]
            max_tokens: Maximum tokens to generate

        Yields:
            Streamed response chunks
        """
        if self.provider == "anthropic":
            yield from self._chat_stream_anthropic(message, history, max_tokens)
        elif self.provider == "sambanova":
            yield from self._chat_stream_sambanova(message, history, max_tokens)
        else:
            yield f"❌ Error: Unsupported provider {self.provider}"

    def _chat_stream_anthropic(
        self,
        message: str,
        history: List[Dict[str, str]] = None,
        max_tokens: int = 4096
    ) -> Generator[str, None, None]:
        """Anthropic-specific streaming implementation with real-time streaming"""
        # Convert Gradio history to Anthropic format
        messages = []
        if history:
            for msg in history:
                role = msg.get("role")
                content = msg.get("content")
                if role and content:
                    messages.append({"role": role, "content": content})

        # Add current message
        messages.append({"role": "user", "content": message})

        try:
            # Initial call with tools
            full_response = ""
            tool_calls_made = []

            while True:
                # Make STREAMING API call with tools
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=SYSTEM_PROMPT,
                    tools=TOOL_DEFINITIONS,
                    messages=messages,
                ) as stream:
                    assistant_content = []
                    current_text = ""
                    tool_uses = []

                    # Stream the response in real-time
                    for event in stream:
                        # Handle different event types
                        if event.type == "content_block_start":
                            if hasattr(event, 'content_block') and event.content_block.type == "text":
                                current_text = ""

                        elif event.type == "content_block_delta":
                            if hasattr(event, 'delta'):
                                if event.delta.type == "text_delta":
                                    # Stream text deltas in real-time!
                                    text_chunk = event.delta.text
                                    current_text += text_chunk
                                    full_response += text_chunk
                                    yield text_chunk  # Real-time streaming!

                        elif event.type == "content_block_stop":
                            if event.content_block.type == "text":
                                assistant_content.append({
                                    "type": "text",
                                    "text": current_text
                                })
                            elif event.content_block.type == "tool_use":
                                tool_uses.append(event.content_block)
                                assistant_content.append({
                                    "type": "tool_use",
                                    "id": event.content_block.id,
                                    "name": event.content_block.name,
                                    "input": event.content_block.input
                                })

                    response = stream.get_final_message()

                # Check stop reason
                if response.stop_reason == "end_turn":
                    # Normal completion - we already streamed the text
                    break

                elif response.stop_reason == "tool_use":
                    # Claude wants to use tools (already extracted in stream loop above)
                    # Add assistant message with tool uses
                    messages.append({
                        "role": "assistant",
                        "content": assistant_content
                    })

                    # Execute tools and collect results
                    tool_results = []
                    for tool_use in tool_uses:
                        # Show tool execution status
                        tool_status = f"\n\n🔧 **Executing: {tool_use.name}**\n"
                        yield tool_status
                        full_response += tool_status

                        # Execute the tool
                        result = execute_tool(tool_use.name, tool_use.input)
                        tool_calls_made.append({
                            "tool": tool_use.name,
                            "input": tool_use.input,
                            "result": result
                        })

                        # Show result summary
                        if result.get("success"):
                            if result.get("url"):
                                result_summary = f"✅ Success! URL: {result.get('url')}\n"
                            elif result.get("total") is not None:
                                result_summary = f"✅ Found {result.get('total')} deployment(s)\n"
                            else:
                                result_summary = "✅ Success!\n"
                        else:
                            result_summary = f"❌ Error: {result.get('error', 'Unknown error')}\n"

                        yield result_summary
                        full_response += result_summary

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result, indent=2)
                        })

                    # Add tool results to messages
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })

                    # Continue the conversation
                    continue

                else:
                    # Unexpected stop reason
                    for block in response.content:
                        if hasattr(block, 'text'):
                            yield block.text
                    break

        except Exception as e:
            yield f"\n\n❌ Error: {str(e)}\n\nPlease check your API key and try again."

    def _chat_stream_sambanova(
        self,
        message: str,
        history: List[Dict[str, str]] = None,
        max_tokens: int = 4096
    ) -> Generator[str, None, None]:
        """SambaNova (OpenAI-compatible) streaming implementation with real-time streaming"""
        # Convert Gradio history to OpenAI format
        messages = []
        if history:
            for msg in history:
                role = msg.get("role")
                content = msg.get("content")
                # SambaNova requires content to be a string, not None or list
                if role and content and isinstance(content, str):
                    messages.append({"role": role, "content": content})

        # Add current message
        messages.append({"role": "user", "content": message})

        # Convert tools to OpenAI format
        openai_tools = self._convert_tools_to_openai_format(TOOL_DEFINITIONS)

        try:
            full_response = ""
            max_iterations = 10  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Make STREAMING API call with tools
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=openai_tools,
                    max_tokens=max_tokens,
                    stream=True,  # Enable streaming!
                )

                # Collect streaming response
                assistant_content = ""
                tool_calls_data = []
                current_tool_call = None

                for chunk in stream:
                    delta = chunk.choices[0].delta

                    # Stream text content in real-time
                    if delta.content:
                        assistant_content += delta.content
                        full_response += delta.content
                        yield delta.content  # Real-time streaming!

                    # Collect tool calls
                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            if tc_delta.index is not None:
                                # Start new tool call or update existing
                                while len(tool_calls_data) <= tc_delta.index:
                                    tool_calls_data.append({
                                        "id": "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""}
                                    })

                                if tc_delta.id:
                                    tool_calls_data[tc_delta.index]["id"] = tc_delta.id
                                if tc_delta.function:
                                    if tc_delta.function.name:
                                        tool_calls_data[tc_delta.index]["function"]["name"] = tc_delta.function.name
                                    if tc_delta.function.arguments:
                                        tool_calls_data[tc_delta.index]["function"]["arguments"] += tc_delta.function.arguments

                # Check if there are tool calls
                if tool_calls_data:
                    # Add assistant message to history
                    messages.append({
                        "role": "assistant",
                        "content": assistant_content,
                        "tool_calls": tool_calls_data
                    })

                    # Execute each tool call
                    for tool_call_data in tool_calls_data:
                        tool_name = tool_call_data["function"]["name"]
                        tool_args = json.loads(tool_call_data["function"]["arguments"])

                        # Show tool execution status
                        tool_status = f"\n\n🔧 **Executing: {tool_name}**\n"
                        yield tool_status
                        full_response += tool_status

                        # Execute the tool
                        result = execute_tool(tool_name, tool_args)

                        # Show result summary
                        if result.get("success"):
                            if result.get("url"):
                                result_summary = f"✅ Success! URL: {result.get('url')}\n"
                            elif result.get("total") is not None:
                                result_summary = f"✅ Found {result.get('total')} deployment(s)\n"
                            else:
                                result_summary = "✅ Success!\n"
                        else:
                            result_summary = f"❌ Error: {result.get('error', 'Unknown error')}\n"

                        yield result_summary
                        full_response += result_summary

                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_data["id"],
                            "content": json.dumps(result, indent=2)
                        })

                    # Continue the loop to get the next response
                    continue

                else:
                    # No tool calls - final response (already streamed above)
                    break

            if iteration >= max_iterations:
                yield f"\n\n⚠️ Warning: Maximum iterations ({max_iterations}) reached. Stopping."

        except Exception as e:
            yield f"\n\n❌ Error: {str(e)}\n\nPlease check your SambaNova configuration and try again."

    def chat_with_tools(
        self,
        message: str,
        history: List[Dict[str, str]] = None,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Non-streaming chat with tool-use support.
        
        Returns the complete response with tool call information.

        Args:
            message: User message
            history: Chat history
            max_tokens: Maximum tokens

        Returns:
            dict with response text, tool calls made, and any deployments created
        """
        # Collect full response from stream
        full_response = ""
        for chunk in self.chat_stream(message, history, max_tokens):
            full_response += chunk
        
        return {
            "success": True,
            "response": full_response
        }

    def generate_mcp_code(
        self,
        description: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate MCP code from a description (legacy method for compatibility).

        Args:
            description: What the MCP server should do
            context: Optional context (existing code, error logs, etc.)

        Returns:
            dict with code, packages, category, tags, and explanation
        """
        prompt = f"Create an MCP server that: {description}"

        if context:
            if context.get("existing_code"):
                prompt += f"\n\nExisting code to modify:\n```python\n{context['existing_code']}\n```"
            if context.get("error"):
                prompt += f"\n\nError to fix:\n{context['error']}"
            if context.get("packages"):
                prompt += f"\n\nCurrent packages: {', '.join(context['packages'])}"

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text

            # Parse the response
            result = self._parse_response(response_text)
            return {
                "success": True,
                **result
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate code: {str(e)}"
            }

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's response to extract code, packages, category, and tags.

        Args:
            response_text: Raw response from Claude

        Returns:
            dict with parsed components
        """
        result = {
            "code": "",
            "packages": [],
            "category": "Uncategorized",
            "tags": [],
            "explanation": ""
        }

        # Extract code block
        import re
        code_match = re.search(r'```python\n(.*?)\n```', response_text, re.DOTALL)
        if code_match:
            result["code"] = code_match.group(1).strip()

        # Extract packages
        packages_match = re.search(r'\*\*Packages:\*\*\s*(.+)', response_text, re.IGNORECASE)
        if packages_match:
            packages_str = packages_match.group(1).strip()
            result["packages"] = [p.strip() for p in packages_str.split(",") if p.strip()]

        # Extract category
        category_match = re.search(r'\*\*Category:\*\*\s*(.+)', response_text, re.IGNORECASE)
        if category_match:
            result["category"] = category_match.group(1).strip()

        # Extract tags
        tags_match = re.search(r'\*\*Tags:\*\*\s*(.+)', response_text, re.IGNORECASE)
        if tags_match:
            tags_str = tags_match.group(1).strip()
            result["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

        # Explanation is everything before the code block
        if code_match:
            result["explanation"] = response_text[:code_match.start()].strip()
        else:
            result["explanation"] = response_text.strip()

        return result

    def review_code(self, code: str) -> Dict[str, Any]:
        """
        Review MCP code for security and best practices.

        Args:
            code: Python code to review

        Returns:
            dict with review results
        """
        prompt = f"""Review this MCP server code for:
1. Security vulnerabilities
2. Error handling
3. Best practices
4. Potential improvements

Code:
```python
{code}
```

Provide a concise review with specific suggestions."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            return {
                "success": True,
                "review": response.content[0].text
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to review code: {str(e)}"
            }


def validate_api_key(api_key: str) -> bool:
    """
    Validate Anthropic API key.

    Args:
        api_key: API key to validate

    Returns:
        True if valid, False otherwise
    """
    if not api_key or not api_key.startswith("sk-ant-"):
        return False

    try:
        client = Anthropic(api_key=api_key)
        # Try a minimal API call
        client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}],
        )
        return True
    except Exception:
        return False


def validate_sambanova_env() -> tuple[bool, str]:
    """
    Validate SambaNova configuration from environment.

    Returns:
        Tuple of (is_valid, message)
    """
    api_key = os.getenv("SAMBANOVA_API_KEY")
    if not api_key:
        return False, "SAMBANOVA_API_KEY not found in environment variables"

    # Optional: Could test the API key here with a minimal call
    # For now, just check if it exists
    return True, "SambaNova configuration found"