"""
Deployment Tools Module

Gradio-based MCP tools for deployment management.
"""

import gradio as gr
import json
import os
import re
import subprocess
import tempfile
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Database imports
from utils.database import db_transaction, get_db
from utils.models import (
    Deployment,
    DeploymentPackage,
    DeploymentFile,
    DeploymentHistory,
)

# Modal wrapper template (same as server.py)
# Note: Tracking code removed - will be developed later
MODAL_WRAPPER_TEMPLATE = '''#!/usr/bin/env python3
"""
Auto-generated Modal deployment for MCP Server: {app_name}
Generated at: {timestamp}
"""

import modal
import os

# App configuration with minimal resources and cold starts allowed
app = modal.App("{app_name}")

# Image with required dependencies
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "fastapi==0.115.14",
    "fastmcp>=2.10.0",
    "pydantic>=2.0.0",
    "requests>=2.28.0",
    "uvicorn>=0.20.0",
    "python-dotenv>=1.0.0",  # For environment variable management
    {extra_deps}
)

# Create secrets from environment variables
# This allows deployed functions to access API keys and other secrets
secrets_dict = {{}}
{env_vars_setup}

# Add webhook configuration to secrets
{webhook_env_vars}

# Create Modal secret from environment variables (if any)
app_secrets = []
if secrets_dict:
    app_secrets = [modal.Secret.from_dict(secrets_dict)]

def make_mcp_server():
    """Create the MCP server with user-defined tools"""
    from dotenv import load_dotenv
    import os

    # Load environment variables from .env file (if present)
    load_dotenv()

    # ============================================================================
    # ⚠️  USER CODE FORMAT (FastMCP Official Pattern)
    # ============================================================================
    # Your tool code MUST follow the standard FastMCP pattern:
    #
    #   from fastmcp import FastMCP
    #   mcp = FastMCP("server-name")
    #
    #   @mcp.tool  # ✅ Preferred (no parentheses)
    #   def my_tool(param: str) -> str:
    #       \"\"\"Tool description\"\"\"
    #       return f"Result: {{param}}"
    #
    # The deployment wrapper:
    # - Uses your code AS-IS (no stripping or modification)
    # - Handles Modal deployment and HTTP transport
    # - Manages environment variables and secrets
    # ============================================================================

    # ============================================================================
    # CONFIGURATION BEST PRACTICE
    # ============================================================================
    # For API keys and configurable values in your tools, use environment vars:
    #
    #   import os
    #   API_KEY = os.getenv('YOUR_API_KEY_NAME', 'fallback_default_value')
    #   BASE_URL = os.getenv('API_BASE_URL', 'https://api.example.com')
    #
    # Benefits:
    # - Update values in Modal settings/secrets without code changes
    # - Keep secrets out of version control
    # - Safe fallback values for development
    #
    # Example in your @mcp.tool functions:
    #
    #   @mcp.tool
    #   def fetch_data(query: str) -> dict:
    #       import os
    #       API_KEY = os.getenv('EXTERNAL_API_KEY', 'demo_key_12345')
    #       # Use API_KEY in your code...
    # ============================================================================

    # === USER-DEFINED TOOLS START ===
    # User's code includes: from fastmcp import FastMCP, mcp = FastMCP(...), and @mcp.tool functions
{user_code_indented}
    # === USER-DEFINED TOOLS END ===

    return mcp


@app.function(
    image=image,
    secrets=app_secrets,  # Pass environment variables to deployed function
    # Cost optimization: minimal resources, allow cold starts
    cpu=0.25,           # 1/4 CPU core (cheapest)
    memory=256,         # 256 MB memory (minimal)
    timeout=300,        # 5 min timeout
    # Scale to zero when not in use (no billing when idle)
    scaledown_window=2, # Scale down after 2 seconds of inactivity
)
@modal.asgi_app()
def web():
    """ASGI web endpoint for the MCP server"""
    from fastapi import FastAPI

    mcp = make_mcp_server()
    mcp_app = mcp.http_app(transport="streamable-http", stateless_http=True)

    fastapi_app = FastAPI(
        title="{server_name}",
        description="Auto-deployed MCP Server on Modal.com",
        lifespan=mcp_app.router.lifespan_context
    )
    fastapi_app.mount("/", mcp_app, "mcp")

    return fastapi_app


# Test function to verify deployment
@app.function(image=image, secrets=app_secrets)
async def test_server():
    """Test the deployed MCP server"""
    import requests

    # Simple HTTP GET test to verify the server is responding
    url = web.get_web_url()
    response = requests.get(url, timeout=30)

    return {{
        "status": "ok" if response.status_code == 200 else "error",
        "status_code": response.status_code,
        "url": url,
        "message": "MCP server is running" if response.status_code == 200 else "Server error"
        }}
'''


# Helper functions (from server.py) - prefixed with _ to hide from MCP auto-discovery
def _generate_app_name(server_name: str) -> str:
    """Generate a unique Modal app name from server name"""
    sanitized = re.sub(r'[^a-z0-9-]', '-', server_name.lower())
    sanitized = re.sub(r'-+', '-', sanitized).strip('-')
    hash_suffix = hashlib.md5(f"{server_name}{datetime.now().isoformat()}".encode()).hexdigest()[:6]
    return f"mcp-{sanitized[:40]}-{hash_suffix}"


def _extract_imports_and_code(user_code: str) -> tuple[list[str], str]:
    """Extract import statements and separate from function code"""
    lines = user_code.strip().split('\n')
    imports = []
    code_lines = []

    for line in lines:
        stripped = line.strip()

        # Detect imports for dependency installation
        if stripped.startswith('import ') or stripped.startswith('from '):
            if stripped.startswith('from '):
                match = re.match(r'from\s+(\w+)', stripped)
                if match:
                    imports.append(match.group(1))
            else:
                match = re.match(r'import\s+(\w+)', stripped)
                if match:
                    imports.append(match.group(1))

        # ⚠️ CRITICAL FIX: Keep FastMCP imports and initialization in user code!
        # The template will use the user's code AS-IS without creating duplicates
        # This ensures @mcp.tool decorators work correctly

        code_lines.append(line)

    return imports, '\n'.join(code_lines)


def _indent_code(code: str, spaces: int = 4) -> str:
    """Indent code by specified number of spaces"""
    indent = ' ' * spaces
    return '\n'.join(indent + line if line.strip() else line for line in code.split('\n'))


def _get_env_vars_for_deployment() -> dict:
    """
    Extract relevant environment variables for Modal deployment.

    Looks for common API key patterns in the environment and returns
    them as a dictionary to be passed to Modal as secrets.

    Returns:
        dict: Environment variables to pass to Modal deployment
    """
    # Common API key patterns to look for
    api_key_patterns = [
        'API_KEY',
        'SECRET_KEY',
        'TOKEN',
        'ACCESS_KEY',
        'CLIENT_SECRET',
        'NEBIUS',
        'OPENAI',
        'ANTHROPIC',
        'GOOGLE',
        'AWS',
        'AZURE'
    ]

    env_vars = {}

    # Check all environment variables
    for key, value in os.environ.items():
        # Include if key matches common API key patterns
        if any(pattern in key.upper() for pattern in api_key_patterns):
            # Exclude database URLs and other sensitive non-API-key vars
            if 'DATABASE' not in key.upper() and 'DB_' not in key.upper():
                env_vars[key] = value

    return env_vars


def _generate_env_vars_setup(env_vars: dict) -> str:
    """
    Generate Python code to set up environment variables in Modal deployment.

    Args:
        env_vars: Dictionary of environment variables

    Returns:
        str: Python code to add to Modal deployment template
    """
    if not env_vars:
        return "# No environment variables to pass"

    lines = []
    for key, value in env_vars.items():
        # Escape the value properly for Python string
        escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
        lines.append(f'secrets_dict["{key}"] = "{escaped_value}"')

    return '\n'.join(lines)


def _extract_tool_definitions(code: str) -> list[dict]:
    """Extract MCP tool definitions from Python code"""
    import ast

    tools = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                has_mcp_decorator = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if (decorator.func.attr == 'tool' and
                                isinstance(decorator.func.value, ast.Name) and
                                decorator.func.value.id == 'mcp'):
                                has_mcp_decorator = True
                                break
                    elif isinstance(decorator, ast.Attribute):
                        if (decorator.attr == 'tool' and
                            isinstance(decorator.value, ast.Name) and
                            decorator.value.id == 'mcp'):
                            has_mcp_decorator = True
                            break

                if has_mcp_decorator:
                    tool_name = node.name
                    docstring = ast.get_docstring(node) or "No description"
                    parameters = []
                    for arg in node.args.args:
                        param_info = {
                            "name": arg.arg,
                            "annotation": None
                        }
                        if arg.annotation:
                            if isinstance(arg.annotation, ast.Name):
                                param_info["annotation"] = arg.annotation.id
                            elif isinstance(arg.annotation, ast.Constant):
                                param_info["annotation"] = str(arg.annotation.value)
                            else:
                                param_info["annotation"] = ast.unparse(arg.annotation)
                        parameters.append(param_info)

                    return_type = None
                    if node.returns:
                        if isinstance(node.returns, ast.Name):
                            return_type = node.returns.id
                        elif isinstance(node.returns, ast.Constant):
                            return_type = str(node.returns.value)
                        else:
                            return_type = ast.unparse(node.returns)

                    tools.append({
                        "name": tool_name,
                        "description": docstring.split('\n')[0] if docstring else "No description",
                        "full_description": docstring,
                        "parameters": parameters,
                        "return_type": return_type
                    })
    except:
        pass

    return tools


# =============================================================================
# MCP TOOL IMPLEMENTATIONS (converted from server.py)
# =============================================================================

def deploy_mcp_server(
    server_name: str,
    mcp_tools_code: str,
    extra_pip_packages: str = "",
    description: str = "",
    category: str = "Uncategorized",
    tags: List[str] = None,
    author: str = "Anonymous",
    version: str = "1.0.0",
    documentation: str = ""
) -> dict:
    """
    Deploy an MCP server with custom tools to Modal.com.

    ═══════════════════════════════════════════════════════════════════════════
    🚨 FOR AI ASSISTANTS: CRITICAL CODE FORMAT REQUIREMENTS 🚨
    ═══════════════════════════════════════════════════════════════════════════

    WHEN GENERATING CODE FOR THIS TOOL, YOU **MUST** FOLLOW THIS EXACT FORMAT:

    **REQUIRED STRUCTURE - COPY THIS TEMPLATE:**
    ```python
    from fastmcp import FastMCP

    mcp = FastMCP("server-name")

    @mcp.tool
    def your_function_name(param: str) -> str:
        \"\"\"Clear description of what this tool does\"\"\"
        # Your implementation here
        return "result"
    ```

    **✅ CRITICAL RULES:**
    1. ✅ MUST start with: `from fastmcp import FastMCP`
    2. ✅ MUST have: `mcp = FastMCP("server-name")`
    3. ✅ MUST use: `@mcp.tool` (NO parentheses unless passing arguments!)
    4. ✅ MUST have: Type hints on ALL parameters and return type
    5. ✅ MUST have: Docstring (triple quotes) for each function
    6. ❌ NEVER include: `mcp.run()` or `if __name__ == "__main__"`

    **🎯 COMPLETE WORKING EXAMPLE:**
    ```python
    from fastmcp import FastMCP

    mcp = FastMCP("weather-api")

    @mcp.tool
    def get_weather(city: str) -> str:
        \"\"\"Get current weather for any city using wttr.in\"\"\"
        import requests
        response = requests.get(f"https://wttr.in/{city}?format=3")
        return response.text

    @mcp.tool
    def get_temperature(city: str, unit: str = "celsius") -> dict:
        \"\"\"Get temperature in celsius or fahrenheit\"\"\"
        import requests
        response = requests.get(f"https://wttr.in/{city}?format=j1")
        data = response.json()
        temp_c = int(data['current_condition'][0]['temp_C'])
        if unit == "fahrenheit":
            return {"temperature": temp_c * 9/5 + 32, "unit": "F"}
        return {"temperature": temp_c, "unit": "C"}
    ```

    **⚠️  COMMON MISTAKES TO AVOID:**
    - ❌ Using `@mcp.tool()` with empty parentheses (use `@mcp.tool` instead)
    - ❌ Forgetting type hints: `def my_tool(x)` → `def my_tool(x: str) -> str`
    - ❌ Missing docstrings
    - ❌ Including `mcp.run()` at the end
    - ❌ Forgetting to import FastMCP

    ═══════════════════════════════════════════════════════════════════════════

    ═══════════════════════════════════════════════════════════════════════════
    📋 KEY REQUIREMENTS (from FastMCP docs)
    ═══════════════════════════════════════════════════════════════════════════

    ✅ MUST HAVE:
    1. `from fastmcp import FastMCP` at the top
    2. `mcp = FastMCP("server-name")` to create the server
    3. `@mcp.tool` or `@mcp.tool()` decorator on each function
    4. Docstring for each tool function
    5. Type hints for all parameters and return type

    💡 Decorator Syntax (both work):
    - `@mcp.tool` - Preferred syntax (cleaner, used in FastMCP docs)
    - `@mcp.tool()` - Also valid (required when passing options like name, enabled, etc.)

    ❌ DO NOT INCLUDE:
    - `mcp.run()` or server startup code
    - `if __name__ == "__main__"` blocks

    💡 The deployment wrapper will handle FastMCP setup, so you can optionally
       omit the import and initialization, but including them is fine too.

    ═══════════════════════════════════════════════════════════════════════════

    ⚡ QUICK START - COPY THIS EXAMPLE:
    ================================

    Step 1: Write your MCP tools code (mcp_tools_code parameter):
    ```python
    from fastmcp import FastMCP

    mcp = FastMCP("cat-facts")

    @mcp.tool
    def get_cat_fact() -> str:
        '''Get a random cat fact from an API'''
        import requests
        response = requests.get("https://catfact.ninja/fact")
        return response.json()["fact"]

    @mcp.tool
    def add_numbers(a: int, b: int) -> int:
        '''Add two numbers together'''
        return a + b
    ```

    Step 2: Call this tool with your code:
    ```python
    result = deploy_mcp_server(
        server_name="cat-facts",
        mcp_tools_code='''
from fastmcp import FastMCP

mcp = FastMCP("cat-facts")

@mcp.tool
def get_cat_fact() -> str:
    import requests
    response = requests.get("https://catfact.ninja/fact")
    return response.json()["fact"]
        ''',
        extra_pip_packages="requests",
        description="Get random cat facts",
        category="Fun",
        tags=["api", "animals"],
        author="Your Name",
        version="1.0.0"
    )
    ```

    Step 3: Use the deployed URL:
    ```
    Your MCP endpoint will be at: https://xxx.modal.run/mcp/
    ```

    ═══════════════════════════════════════════════════════════════════════════
    📝 CODE STRUCTURE - DETAILED EXPLANATION
    ═══════════════════════════════════════════════════════════════════════════

    ⚠️  IMPORTANT - READ THIS CAREFULLY:

    The deployment wrapper already creates the MCP server instance for you.
    Your code must include `from fastmcp import FastMCP`, create an MCP instance,
    and decorate your functions with `@mcp.tool` (no parentheses).

    ✅ CORRECT FORMAT (from FastMCP official docs):
    ─────────────────────────────────────────────────
    ```python
    from fastmcp import FastMCP

    mcp = FastMCP("server-name")

    @mcp.tool
    def my_tool(param: str) -> str:
        '''Tool description'''
        return f"Result: {param}"
    ```

    💡 Note: Both `@mcp.tool` and `@mcp.tool()` work!
    - `@mcp.tool` - Cleaner (preferred in FastMCP docs)
    - `@mcp.tool()` - Also valid, required when passing options:
    ```python
    @mcp.tool(name="custom_name", description="Custom description", enabled=True)
    def my_function():
        pass
    ```

    🔧 WHAT THE WRAPPER PROVIDES AUTOMATICALLY:
    ────────────────────────────────────────────
    ✅ from fastmcp import FastMCP
    ✅ mcp = FastMCP("{server_name}")
    ✅ Server initialization and configuration
    ✅ Modal deployment wrapper
    ✅ HTTP transport setup
    ✅ Environment variable loading

    📋 WHAT YOU MUST PROVIDE (required by FastMCP):
    ────────────────────────────────────────────────
    ✅ `from fastmcp import FastMCP` import statement
    ✅ `mcp = FastMCP("server-name")` initialization
    ✅ One or more functions decorated with `@mcp.tool` or `@mcp.tool()`
    ✅ Docstrings for each tool (becomes tool description in MCP)
    ✅ Type hints for all parameters (str, int, bool, dict, list, etc.)
    ✅ Type hint for return value
    ✅ Any Python imports your code needs (can go at top or inside functions)

    ❌ DO NOT INCLUDE THESE:
    ────────────────────────
    ❌ mcp.run()                       ← Wrapper handles server startup
    ❌ if __name__ == "__main__"       ← Not needed in deployment
    ❌ Modal imports (modal.App, etc.) ← Wrapper handles Modal setup

    💡 The wrapper will auto-strip duplicate FastMCP imports if present

    ═══════════════════════════════════════════════════════════════════════════

    💡 MORE EXAMPLES:
    ================

    Example 1 - Simple Calculator:
    ```python
    from fastmcp import FastMCP

    mcp = FastMCP("calculator")

    @mcp.tool
    def calculate(expression: str) -> float:
        '''Safely evaluate a math expression'''
        import ast
        import operator

        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
        }

        def eval_expr(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
            else:
                raise ValueError("Invalid expression")

        return eval_expr(ast.parse(expression, mode='eval').body)
    ```

    Example 2 - Weather API with Error Handling (requires API key):
    ```python
    from fastmcp import FastMCP

    mcp = FastMCP("weather")

    @mcp.tool
    def get_weather(city: str) -> dict:
        '''Get current weather for a city.

        IMPORTANT: Always returns dict (never None) to match return type!
        Returns error dict if request fails.
        '''
        import requests
        import os

        api_key = os.environ.get("OPENWEATHER_API_KEY", "demo")
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": api_key, "units": "metric"}

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return {
                "city": city,
                "temperature": data["main"]["temp"],
                "description": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"]
            }
        except Exception as e:
            # Return error dict (not None!) to match return type
            return {"error": str(e), "city": city}
    ```

    Example 3 - Using Optional for Nullable Returns:
    ```python
    from fastmcp import FastMCP
    from typing import Optional

    mcp = FastMCP("data-tools")

    @mcp.tool
    def find_user(user_id: int) -> Optional[dict]:
        '''Find a user by ID. Returns None if not found.

        Using Optional[dict] allows returning None!
        '''
        users = {
            1: {"name": "Alice", "email": "alice@example.com"},
            2: {"name": "Bob", "email": "bob@example.com"}
        }

        # Can return None because of Optional
        return users.get(user_id)  # Returns None if not found
    ```

    Example 4 - Multiple Tools in One Server:
    ```python
    from fastmcp import FastMCP

    mcp = FastMCP("text-tools")

    @mcp.tool
    def count_words(text: str) -> int:
        '''Count words in text'''
        return len(text.split())

    @mcp.tool
    def reverse_text(text: str) -> str:
        '''Reverse the text'''
        return text[::-1]

    @mcp.tool
    def to_uppercase(text: str) -> str:
        '''Convert text to uppercase'''
        return text.upper()
    ```

    📦 PARAMETERS EXPLAINED:
    ========================

    Args:
        server_name (str, REQUIRED):
            Unique name for your MCP server. Use lowercase with hyphens.
            Examples: "weather-api", "cat-facts", "calculator-tool"

        mcp_tools_code (str, REQUIRED):
            ⚠️  IMPORTANT: Must be complete FastMCP server code!

            ✅ MUST include (per FastMCP docs):
            - from fastmcp import FastMCP
            - mcp = FastMCP("server-name")
            - @mcp.tool decorated functions (NO parentheses!)
            - Function docstrings
            - Type hints for all parameters and return values

            ❌ DO NOT include:
            - mcp.run() or server startup code
            - if __name__ == "__main__" blocks

            See "SIMPLE EXAMPLE - COPY THIS EXACTLY" section above for template.
            The wrapper will handle Modal deployment and auto-strip duplicate imports.

        extra_pip_packages (str, optional):
            Comma-separated list of PyPI packages your code needs.
            Examples: "requests", "pandas,numpy", "beautifulsoup4,requests"
            The system auto-detects some imports, but always specify to be safe!

        description (str, optional):
            Human-readable description of what your server does.
            Example: "Provides weather data and forecasts for any city"

        category (str, optional):
            Category for organizing your servers.
            Examples: "Weather", "Finance", "Utilities", "Fun", "Data"
            Default: "Uncategorized"

        tags (List[str], optional):
            List of tags for filtering and search.
            Examples: ["api", "weather"], ["finance", "stocks", "data"]
            Default: []

        author (str, optional):
            Your name or organization.
            Default: "Anonymous"

        version (str, optional):
            Semantic version for your server.
            Examples: "1.0.0", "2.1.0", "0.0.1"
            Default: "1.0.0"

        documentation (str, optional):
            Markdown documentation for your server.
            Default: ""

    Returns:
        dict: Deployment result with the following structure:
        {
            "success": bool,              # True if deployment succeeded
            "app_name": str,              # Modal app name (e.g., "mcp-weather-abc123")
            "url": str,                   # Base URL (e.g., "https://xxx.modal.run")
            "mcp_endpoint": str,          # Full MCP endpoint URL (url + "/mcp/")
            "deployment_id": str,         # Unique ID for this deployment
            "detected_packages": list,    # Auto-detected Python packages
            "security_scan": dict,        # Security scan results
            "message": str                # Human-readable success/error message
        }

        On error:
        {
            "success": False,
            "error": str,                 # Error message
            "security_scan": dict,        # If security issues found
            "severity": str,              # "low", "medium", "high", or "critical"
            "issues": list,               # List of security issues
            "explanation": str            # Detailed explanation
        }

    🔒 SECURITY:
    ===========
    All code is automatically scanned for security vulnerabilities before deployment.
    Deployments with HIGH or CRITICAL severity issues will be blocked.

    ⚠️  COMMON ERRORS & FIXES:
    ==========================

    Error: "Invalid Python code"
    Fix: Check your code syntax. Test it locally first!

    Error: "No @mcp.tool decorators found"
    Fix: Make sure you have at least one function with @mcp.tool (no parentheses!)

    Error: "Module 'xyz' not found"
    Fix: Add the package to extra_pip_packages parameter

    Error: "Security vulnerabilities detected"
    Fix: Review the security scan output and fix the issues

    Error: "Input validation error: None is not of type 'array'"
    Fix: TYPE HINT MISMATCH! Your function's return type doesn't match what it actually returns.

    Common causes:
    - Function returns None but type hint says list: `-> list`
    - Function returns None but type hint says dict: `-> dict`
    - Function can return None but type hint doesn't allow it

    Solutions:
    ✅ If function can return None, use Optional:
       from typing import Optional
       def my_tool() -> Optional[list]:  # Can return list or None
           if error:
               return None
           return [1, 2, 3]

    ✅ If function always returns a value, ensure it does:
       def my_tool() -> list:
           if error:
               return []  # Return empty list, not None
           return [1, 2, 3]

    ✅ Match your return type to what you actually return:
       def my_tool() -> str:  # Says returns string
           return "result"     # Actually returns string ✅

       def my_tool() -> dict:  # Says returns dict
           return None         # Actually returns None ❌ WRONG!

       def my_tool() -> dict:  # Says returns dict
           return {"key": "value"}  # Actually returns dict ✅

    💰 COST & PERFORMANCE:
    =====================

    Your deployed server will:
    - Use 0.25 CPU cores (1/4 core) - cheapest tier
    - Use 256 MB RAM - minimal memory
    - Scale to ZERO when not in use (NO BILLING when idle!)
    - Cold start in 2-5 seconds when first called
    - Auto-scale up based on traffic
    - Timeout after 5 minutes of processing

    🚀 AFTER DEPLOYMENT:
    ===================

    1. Your server will be available at: https://xxx.modal.run/mcp/
    2. Add it to Claude Desktop config:
       {
         "mcpServers": {
           "your-server": {
             "url": "https://xxx.modal.run/mcp/"
           }
         }
       }
    3. Test it using MCP Inspector:
       npx @modelcontextprotocol/inspector https://xxx.modal.run/mcp/
    """
    try:
        # === VALIDATION PHASE ===
        # Validate required parameters
        if not server_name or not server_name.strip():
            return {
                "success": False,
                "error": "server_name is required and cannot be empty",
                "message": "❌ Please provide a server name (e.g., 'weather-api', 'cat-facts')"
            }

        if not mcp_tools_code or not mcp_tools_code.strip():
            return {
                "success": False,
                "error": "mcp_tools_code is required and cannot be empty",
                "message": "❌ Please provide your MCP tools code. See the tool description for examples!"
            }

        # Validate code contains at least one @mcp.tool or @mcp.tool() decorator
        if "@mcp.tool" not in mcp_tools_code:
            return {
                "success": False,
                "error": "Code must have at least one @mcp.tool decorator",
                "message": "❌ Your code must include at least one tool with @mcp.tool decorator\n\n"
                          "Example:\n"
                          "from fastmcp import FastMCP\n"
                          "mcp = FastMCP('server-name')\n\n"
                          "@mcp.tool\n"
                          "def my_tool(param: str) -> str:\n"
                          "    '''Tool description'''\n"
                          "    return f'Result: {param}'\n\n"
                          "See the tool description for complete examples!"
            }

        # ⚠️ CRITICAL FIX: Do NOT strip FastMCP imports/initialization from user code!
        # The _extract_imports_and_code() function will handle this properly
        # by keeping the code intact and only extracting import info for pip packages
        import re

        # Convert comma-separated packages to list
        extra_pip_packages_list = [p.strip() for p in extra_pip_packages.split(",")] if extra_pip_packages else []

        # Handle tags parameter
        tags_list = tags if tags is not None else []

        # Generate unique app name
        app_name = _generate_app_name(server_name)

        # Generate deployment_id early so it can be used in webhook configuration
        deployment_id = f"deploy-{app_name}"

        # Extract imports and prepare extra dependencies
        detected_imports, cleaned_code = _extract_imports_and_code(mcp_tools_code)
        all_packages = list(set(detected_imports + extra_pip_packages_list))

        # Filter out standard library packages
        stdlib = {'os', 'sys', 'json', 're', 'datetime', 'time', 'typing', 'pathlib',
                  'collections', 'functools', 'itertools', 'math', 'random', 'string',
                  'hashlib', 'base64', 'urllib', 'zoneinfo', 'asyncio'}
        extra_deps = [pkg for pkg in all_packages if pkg.lower() not in stdlib]

        # === SECURITY SCAN PHASE ===
        from utils.security_scanner import scan_code_for_security

        scan_result = scan_code_for_security(
            code=cleaned_code,
            context={
                "server_name": server_name,
                "packages": extra_deps,
                "description": description
            }
        )

        if scan_result["severity"] in ["high", "critical"]:
            return {
                "success": False,
                "error": "Security vulnerabilities detected - deployment blocked",
                "security_scan": scan_result,
                "severity": scan_result["severity"],
                "issues": scan_result["issues"],
                "explanation": scan_result["explanation"],
                "message": f"🚫 Deployment blocked due to {scan_result['severity']} severity security issues"
            }

        # Format extra dependencies for template
        extra_deps_str = ',\n    '.join(f'"{pkg}"' for pkg in extra_deps) if extra_deps else ''
        user_code_indented = _indent_code(cleaned_code, spaces=4)

        # Get environment variables for Modal deployment
        env_vars = _get_env_vars_for_deployment()
        env_vars_setup = _generate_env_vars_setup(env_vars)

        # Generate webhook configuration
        webhook_url = os.getenv('MCP_WEBHOOK_URL', '')
        if not webhook_url:
            base_url = os.getenv('MCP_BASE_URL', 'http://localhost:7860')
            webhook_url = f"{base_url}/api/webhook/usage"

        webhook_env_vars_code = f'''
secrets_dict["MCP_WEBHOOK_URL"] = "{webhook_url}"
secrets_dict["MCP_DEPLOYMENT_ID"] = "{deployment_id}"
'''

        # Generate Modal wrapper code (tracking removed - will be developed later)
        modal_code = MODAL_WRAPPER_TEMPLATE.format(
            app_name=app_name,
            server_name=server_name,
            timestamp=datetime.now().isoformat(),
            extra_deps=extra_deps_str,
            user_code_indented=user_code_indented,
            env_vars_setup=env_vars_setup,
            webhook_env_vars=webhook_env_vars_code
        )

        # Create temporary deployment directory (will be cleaned up after deployment)
        temp_deploy_dir = tempfile.mkdtemp(prefix=f"mcp_deploy_{app_name}_")
        try:
            deploy_dir_path = Path(temp_deploy_dir)
            deploy_file = deploy_dir_path / "app.py"
            deploy_file.write_text(modal_code)
            (deploy_dir_path / "original_tools.py").write_text(mcp_tools_code)

            # Deploy to Modal
            result = subprocess.run(
                ["modal", "deploy", str(deploy_file)],
                capture_output=True,
                text=True,
                timeout=300
            )
        finally:
            # Clean up temporary deployment directory
            try:
                shutil.rmtree(temp_deploy_dir)
            except Exception:
                pass  # Ignore cleanup errors

        if result.returncode != 0:
            return {
                "success": False,
                "error": "Deployment failed",
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        # Extract URL from deployment output
        url_match = re.search(r'https://[a-zA-Z0-9-]+--[a-zA-Z0-9-]+\.modal\.run', result.stdout)
        deployed_url = url_match.group(0) if url_match else None

        if not deployed_url:
            try:
                import modal
                remote_func = modal.Function.from_name(app_name, "web")
                deployed_url = remote_func.get_web_url()
            except Exception:
                deployed_url = f"https://<workspace>--{app_name}-web.modal.run"

        # Save to database (deployment_id already created earlier)
        with db_transaction() as db:
            deployment = Deployment(
                deployment_id=deployment_id,
                app_name=app_name,
                server_name=server_name,
                url=deployed_url,
                mcp_endpoint=f"{deployed_url}/mcp/" if deployed_url else None,
                description=description,
                status="deployed",
                category=category,
                tags=tags_list,
                author=author,
                version=version,
                documentation=documentation,
            )
            db.add(deployment)
            db.flush()

            for package in extra_deps:
                pkg = DeploymentPackage(deployment_id=deployment_id, package_name=package)
                db.add(pkg)

            # Store files in database only (no local file paths)
            app_file = DeploymentFile(
                deployment_id=deployment_id,
                file_type="app",
                file_path="",  # No persistent local file
                file_content=modal_code,
            )
            db.add(app_file)

            original_file = DeploymentFile(
                deployment_id=deployment_id,
                file_type="original_tools",
                file_path="",  # No persistent local file
                file_content=mcp_tools_code,
            )
            db.add(original_file)

            tools_list = _extract_tool_definitions(cleaned_code)
            tools_manifest = DeploymentFile(
                deployment_id=deployment_id,
                file_type="tools_manifest",
                file_path="",
                file_content=json.dumps(tools_list, indent=2),
            )
            db.add(tools_manifest)

            DeploymentHistory.log_event(
                db=db,
                deployment_id=deployment_id,
                action="created",
                details={
                    "server_name": server_name,
                    "packages": extra_deps,
                    "deployed_url": deployed_url,
                },
            )

            scan_action = "security_scan_passed" if scan_result["is_safe"] else "security_scan_warning"
            DeploymentHistory.log_event(
                db=db,
                deployment_id=deployment_id,
                action=scan_action,
                details={
                    "severity": scan_result["severity"],
                    "is_safe": scan_result["is_safe"],
                    "explanation": scan_result["explanation"],
                }
            )

        security_msg = ""
        if scan_result["severity"] in ["low", "medium"]:
            security_msg = f"\n⚠️  Security Warning ({scan_result['severity']} severity): {scan_result['explanation']}"
        elif scan_result["is_safe"]:
            security_msg = "\n✅ Security scan passed"

        # Generate Claude Desktop integration config
        mcp_endpoint = f"{deployed_url}/mcp/" if deployed_url else None
        claude_desktop_config = {
            server_name: {
                "command": "npx",
                "args": [
                    "mcp-remote",
                    mcp_endpoint
                ]
            }
        } if mcp_endpoint else {}

        config_locations = {
            "macOS": "~/Library/Application Support/Claude/claude_desktop_config.json",
            "Windows": "%APPDATA%/Claude/claude_desktop_config.json",
            "Linux": "~/.config/Claude/claude_desktop_config.json"
        }

        return {
            "success": True,
            "app_name": app_name,
            "url": deployed_url,
            "mcp_endpoint": mcp_endpoint,
            "deployment_id": deployment_id,
            "security_scan": scan_result,
            "claude_desktop_config": claude_desktop_config,
            "config_locations": config_locations,
            "message": f"✅ Successfully deployed '{server_name}'\n🔗 URL: {deployed_url}\n📡 MCP: {mcp_endpoint}{security_msg}\n\n🔌 **Connect to Claude Desktop:**\nAdd this to your claude_desktop_config.json:\n```json\n{json.dumps(claude_desktop_config, indent=2)}\n```"
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Deployment timed out after 5 minutes"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_deployments() -> dict:
    """
    List all deployed MCP servers.

    Returns:
        dict with deployment list and statistics
    """
    try:
        with get_db() as db:
            deployments = Deployment.get_active_deployments(db)
            deployment_list = []
            for dep in deployments:
                deployment_list.append({
                    "deployment_id": dep.deployment_id,
                    "app_name": dep.app_name,
                    "server_name": dep.server_name,
                    "url": dep.url,
                    "mcp_endpoint": dep.mcp_endpoint,
                    "status": dep.status,
                    "created_at": dep.created_at.isoformat() if dep.created_at else None,
                    "description": dep.description,
                })

            return {
                "success": True,
                "total": len(deployment_list),
                "deployments": deployment_list
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_deployment_status(deployment_id: str = "", app_name: str = "") -> dict:
    """
    Get detailed status of a deployed MCP server.

    Args:
        deployment_id: The deployment ID
        app_name: Or the Modal app name

    Returns:
        dict with deployment details and status
    """
    try:
        with db_transaction() as db:
            deployment = None
            if deployment_id:
                deployment = Deployment.get_by_deployment_id(db, deployment_id)
            elif app_name:
                deployment = Deployment.get_by_app_name(db, app_name)

            if not deployment:
                return {
                    "success": False,
                    "error": f"Deployment not found: {deployment_id or app_name}"
                }

            live = False
            try:
                import modal
                remote_func = modal.Function.from_name(deployment.app_name, "web")
                current_url = remote_func.get_web_url()
                if current_url != deployment.url:
                    deployment.url = current_url
                    deployment.mcp_endpoint = f"{current_url}/mcp/"
                live = True
            except Exception:
                live = False

            # Return only deployment-related info (no usage metrics)
            return {
                "success": True,
                "live": live,
                "deployment_id": deployment.deployment_id,
                "app_name": deployment.app_name,
                "server_name": deployment.server_name,
                "url": deployment.url,
                "mcp_endpoint": deployment.mcp_endpoint,
                "description": deployment.description,
                "status": deployment.status,
                "category": deployment.category,
                "tags": deployment.tags or [],
                "author": deployment.author,
                "version": deployment.version,
                "documentation": deployment.documentation,
                "created_at": deployment.created_at.isoformat() if deployment.created_at else None,
                "updated_at": deployment.updated_at.isoformat() if deployment.updated_at else None,
                "packages": [pkg.package_name for pkg in deployment.packages],
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_deployment(deployment_id: str = "", app_name: str = "", confirm: bool = False) -> dict:
    """
    Delete a deployed MCP server from Modal.

    Args:
        deployment_id: The deployment ID to delete
        app_name: Or the Modal app name
        confirm: Must be True to confirm deletion

    Returns:
        dict with deletion status
    """
    if not confirm:
        return {"success": False, "error": "Must set confirm=True to delete deployment"}

    try:
        with db_transaction() as db:
            deployment = None
            if deployment_id:
                deployment = Deployment.get_by_deployment_id(db, deployment_id)
            elif app_name:
                deployment = Deployment.get_by_app_name(db, app_name)

            if not deployment:
                return {"success": False, "error": f"Deployment not found: {deployment_id or app_name}"}

            target_app_name = deployment.app_name
            found_id = deployment.deployment_id

            # Stop the Modal app
            try:
                subprocess.run(
                    ["modal", "app", "stop", target_app_name],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            except subprocess.TimeoutExpired:
                return {"success": False, "error": "Modal app stop timed out"}

            # Soft delete in database (no local files to clean up)
            deployment.soft_delete()
            DeploymentHistory.log_event(
                db=db,
                deployment_id=found_id,
                action="deleted",
                details={"app_name": target_app_name},
            )

            return {
                "success": True,
                "app_name": target_app_name,
                "deployment_id": found_id,
                "message": f"✅ Deleted deployment '{target_app_name}'"
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_deployment_code(deployment_id: str) -> dict:
    """
    Get the current MCP tools code for a deployment.

    Args:
        deployment_id: The deployment ID

    Returns:
        dict with code, packages, and tool information
    """
    try:
        with get_db() as db:
            deployment = Deployment.get_by_deployment_id(db, deployment_id)
            if not deployment:
                return {"success": False, "error": f"Deployment not found: {deployment_id}"}

            original_file = DeploymentFile.get_file(db, deployment_id, "original_tools")
            if not original_file:
                return {"success": False, "error": f"No code found for deployment: {deployment_id}"}

            # Get packages using the relationship or direct query
            packages = db.query(DeploymentPackage).filter_by(deployment_id=deployment_id).all()
            package_list = [pkg.package_name for pkg in packages]

            tools_manifest = DeploymentFile.get_file(db, deployment_id, "tools_manifest")
            tools_list = []
            if tools_manifest and tools_manifest.file_content:
                try:
                    tools_list = json.loads(tools_manifest.file_content)
                except json.JSONDecodeError:
                    tools_list = []

            return {
                "success": True,
                "deployment_id": deployment.deployment_id,
                "server_name": deployment.server_name,
                "description": deployment.description or "",      
                "url": deployment.url or "",                      
                "mcp_endpoint": deployment.mcp_endpoint or "",    
                "code": original_file.file_content or "",         
                "packages": package_list,
                "tools": tools_list,
                "message": f"✅ Retrieved code for '{deployment.server_name}'"
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def _validate_python_syntax(code: str) -> dict:
    """
    Validate Python code syntax.

    Args:
        code: Python code to validate

    Returns:
        dict with success status and error message if invalid
    """
    try:
        compile(code, '<string>', 'exec')
        return {"valid": True}
    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"Syntax error at line {e.lineno}: {e.msg}"
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Validation error: {str(e)}"
        }


def _validate_packages(packages: list[str]) -> dict:
    """
    Validate package names.

    Args:
        packages: List of package names to validate

    Returns:
        dict with validation results
    """
    if not packages:
        return {"valid": True, "packages": []}

    # Basic validation: check for valid package name format
    package_pattern = re.compile(r'^[a-zA-Z0-9_\-\.]+$')

    invalid_packages = []
    valid_packages = []

    for pkg in packages:
        if not pkg or not package_pattern.match(pkg):
            invalid_packages.append(pkg)
        else:
            valid_packages.append(pkg)

    if invalid_packages:
        return {
            "valid": False,
            "error": f"Invalid package names: {', '.join(invalid_packages)}",
            "invalid_packages": invalid_packages
        }

    return {
        "valid": True,
        "packages": valid_packages
    }


def _backup_deployment_state(db, deployment: Deployment) -> dict:
    """
    Backup current deployment state to deployment_history.

    Args:
        db: Database session
        deployment: Deployment object to backup

    Returns:
        dict with backup details
    """
    try:
        # Get current packages using direct query
        packages = db.query(DeploymentPackage).filter_by(deployment_id=deployment.deployment_id).all()
        package_list = [pkg.package_name for pkg in packages]

        # Get current files
        original_file = DeploymentFile.get_file(db, deployment.deployment_id, "original_tools")
        app_file = DeploymentFile.get_file(db, deployment.deployment_id, "app")

        backup_details = {
            "server_name": deployment.server_name,
            "description": deployment.description,
            "url": deployment.url,
            "mcp_endpoint": deployment.mcp_endpoint,
            "status": deployment.status,
            "packages": package_list,
            "original_tools_code": original_file.file_content if original_file else None,
            "app_code": app_file.file_content if app_file else None,
        }

        # Log backup event
        DeploymentHistory.log_event(
            db=db,
            deployment_id=deployment.deployment_id,
            action="pre_update_backup",
            details=backup_details
        )

        return {
            "success": True,
            "backup_details": backup_details
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Backup failed: {str(e)}"
        }


def _test_updated_deployment(url: str, timeout: int = 30) -> dict:
    """
    Test if an updated deployment is responsive.

    Args:
        url: Deployment URL to test
        timeout: Request timeout in seconds

    Returns:
        dict with test results
    """
    try:
        import requests

        response = requests.get(url, timeout=timeout)

        if response.status_code == 200:
            return {
                "success": True,
                "responsive": True,
                "status_code": response.status_code
            }
        else:
            return {
                "success": False,
                "responsive": False,
                "status_code": response.status_code,
                "error": f"Server returned status {response.status_code}"
            }

    except Exception as e:
        return {
            "success": False,
            "responsive": False,
            "error": f"Test failed: {str(e)}"
        }


def update_deployment_code(
    deployment_id: str,
    mcp_tools_code: str = None,
    extra_pip_packages: list[str] = None,
    server_name: str = None,
    description: str = None
) -> dict:
    """
    Update deployment code and/or packages with redeployment to Modal.

    This will redeploy the MCP server with new code/packages while preserving
    the same URL (by reusing the same Modal app_name). The deployment will
    experience brief downtime (5-10 seconds) during the update.

    Args:
        deployment_id: The deployment ID to update (e.g., "deploy-mcp-xxx-xxxxxx")
        mcp_tools_code: New MCP tools code (optional - triggers redeployment)
        extra_pip_packages: New package list (optional - triggers redeployment)
        server_name: New server name (optional)
        description: New description (optional)

    Returns:
        dict with update status, URL, and deployment info
    """
    try:
        # Validate at least one field is provided
        if not any([mcp_tools_code, extra_pip_packages is not None, server_name, description is not None]):
            return {
                "success": False,
                "error": "Must provide at least one field to update"
            }

        with db_transaction() as db:
            # Find deployment
            deployment = Deployment.get_by_deployment_id(db, deployment_id)

            if not deployment:
                return {
                    "success": False,
                    "error": f"Deployment not found: {deployment_id}"
                }

            if deployment.is_deleted:
                return {
                    "success": False,
                    "error": "Cannot update deleted deployment"
                }

            # Track what we're updating
            updated_fields = []
            requires_redeployment = False

            # === VALIDATION PHASE ===

            # Validate new code syntax if provided
            if mcp_tools_code:
                validation = _validate_python_syntax(mcp_tools_code)
                if not validation["valid"]:
                    return {
                        "success": False,
                        "error": f"Invalid Python code: {validation['error']}"
                    }
                requires_redeployment = True
                updated_fields.append("mcp_tools_code")

            # Validate packages if provided
            if extra_pip_packages is not None:
                validation = _validate_packages(extra_pip_packages)
                if not validation["valid"]:
                    return {
                        "success": False,
                        "error": f"Invalid packages: {validation['error']}"
                    }
                requires_redeployment = True
                updated_fields.append("packages")

            # Validate metadata
            if server_name:
                if not server_name.strip():
                    return {
                        "success": False,
                        "error": "server_name cannot be empty"
                    }
                updated_fields.append("server_name")

            if description is not None:
                updated_fields.append("description")

            # === BACKUP PHASE ===

            # Always backup before any update
            backup_result = _backup_deployment_state(db, deployment)
            if not backup_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to backup deployment: {backup_result['error']}"
                }

            # === UPDATE PHASE ===

            # If only metadata changed, skip redeployment
            if not requires_redeployment:
                # Update metadata only
                if server_name:
                    deployment.server_name = server_name.strip()
                if description is not None:
                    deployment.description = description

                # Log metadata-only update
                DeploymentHistory.log_event(
                    db=db,
                    deployment_id=deployment_id,
                    action="metadata_updated",
                    details={
                        "updated_fields": updated_fields,
                        "redeployed": False
                    }
                )

                return {
                    "success": True,
                    "redeployed": False,
                    "updated_fields": updated_fields,
                    "deployment": {
                        "deployment_id": deployment.deployment_id,
                        "app_name": deployment.app_name,
                        "server_name": deployment.server_name,
                        "url": deployment.url,
                        "mcp_endpoint": deployment.mcp_endpoint,
                        "description": deployment.description,
                        "status": deployment.status,
                        "category": deployment.category,
                        "tags": deployment.tags or [],
                        "author": deployment.author,
                        "version": deployment.version,
                        "created_at": deployment.created_at.isoformat() if deployment.created_at else None,
                        "updated_at": deployment.updated_at.isoformat() if deployment.updated_at else None,
                    },
                    "message": f"✅ Updated metadata for '{deployment_id}' (no redeployment needed)"
                }

            # === REDEPLOYMENT PHASE ===

            # Get current or new values
            final_server_name = server_name.strip() if server_name else deployment.server_name
            final_tools_code = mcp_tools_code if mcp_tools_code else None
            final_packages = extra_pip_packages if extra_pip_packages is not None else None

            # If code not provided, get from database
            if not final_tools_code:
                original_file = DeploymentFile.get_file(db, deployment_id, "original_tools")
                if not original_file:
                    return {
                        "success": False,
                        "error": "Cannot find original tools code in database"
                    }
                final_tools_code = original_file.file_content

            # If packages not provided, get from database
            if final_packages is None:
                current_packages = db.query(DeploymentPackage).filter_by(deployment_id=deployment_id).all()
                final_packages = [pkg.package_name for pkg in current_packages]

            # Extract imports and prepare dependencies
            detected_imports, cleaned_code = _extract_imports_and_code(final_tools_code)
            all_packages = list(set(detected_imports + final_packages))

            # Filter out standard library packages
            stdlib = {'os', 'sys', 'json', 're', 'datetime', 'time', 'typing', 'pathlib',
                      'collections', 'functools', 'itertools', 'math', 'random', 'string',
                      'hashlib', 'base64', 'urllib', 'zoneinfo', 'asyncio'}
            extra_deps = [pkg for pkg in all_packages if pkg.lower() not in stdlib]

            # === SECURITY SCAN PHASE ===
            from utils.security_scanner import scan_code_for_security

            scan_result = scan_code_for_security(
                code=cleaned_code,
                context={
                    "server_name": final_server_name,
                    "packages": extra_deps,
                    "description": description or deployment.description or "",
                    "deployment_id": deployment_id
                }
            )

            # Check if redeployment should be blocked
            if scan_result["severity"] in ["high", "critical"]:
                return {
                    "success": False,
                    "error": "Security vulnerabilities detected - update blocked",
                    "security_scan": scan_result,
                    "severity": scan_result["severity"],
                    "message": f"🚫 Update blocked due to {scan_result['severity']} severity security issues"
                }

            # Format extra dependencies for template
            extra_deps_str = ',\n    '.join(f'"{pkg}"' for pkg in extra_deps) if extra_deps else ''
            user_code_indented = _indent_code(cleaned_code, spaces=4)

            # Get environment variables for Modal deployment
            env_vars = _get_env_vars_for_deployment()
            env_vars_setup = _generate_env_vars_setup(env_vars)

            # Generate webhook configuration
            webhook_url = os.getenv('MCP_WEBHOOK_URL', '')
            if not webhook_url:
                base_url = os.getenv('MCP_BASE_URL', 'http://localhost:7860')
                webhook_url = f"{base_url}/api/webhook/usage"

            webhook_env_vars_code = f'''
secrets_dict["MCP_WEBHOOK_URL"] = "{webhook_url}"
secrets_dict["MCP_DEPLOYMENT_ID"] = "{deployment_id}"
'''

            # Generate Modal wrapper code (reuse same app_name to preserve URL)
            # Note: Tracking removed - will be developed later
            modal_code = MODAL_WRAPPER_TEMPLATE.format(
                app_name=deployment.app_name,  # IMPORTANT: Reuse existing app_name
                server_name=final_server_name,
                timestamp=datetime.now().isoformat(),
                extra_deps=extra_deps_str,
                user_code_indented=user_code_indented,
                env_vars_setup=env_vars_setup,
                webhook_env_vars=webhook_env_vars_code
            )

            # Create temporary deployment directory (will be cleaned up after deployment)
            temp_deploy_dir = tempfile.mkdtemp(prefix=f"mcp_update_{deployment.app_name}_")
            try:
                deploy_dir_path = Path(temp_deploy_dir)
                deploy_file = deploy_dir_path / "app.py"
                deploy_file.write_text(modal_code)
                (deploy_dir_path / "original_tools.py").write_text(final_tools_code)

                # Deploy to Modal (reusing same app_name)
                result = subprocess.run(
                    ["modal", "deploy", str(deploy_file)],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            finally:
                # Clean up temporary deployment directory
                try:
                    shutil.rmtree(temp_deploy_dir)
                except Exception:
                    pass  # Ignore cleanup errors

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": "Redeployment failed",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }

            # Extract URL from deployment output
            url_match = re.search(r'https://[a-zA-Z0-9-]+--[a-zA-Z0-9-]+\.modal\.run', result.stdout)
            deployed_url = url_match.group(0) if url_match else None

            if not deployed_url:
                try:
                    import modal
                    remote_func = modal.Function.from_name(deployment.app_name, "web")
                    deployed_url = remote_func.get_web_url()
                except Exception:
                    deployed_url = deployment.url

            # === DATABASE UPDATE PHASE ===

            # Update deployment record
            if server_name:
                deployment.server_name = server_name.strip()
            if description is not None:
                deployment.description = description
            deployment.url = deployed_url
            deployment.mcp_endpoint = f"{deployed_url}/mcp/" if deployed_url else None

            # Update packages
            db.query(DeploymentPackage).filter(
                DeploymentPackage.deployment_id == deployment_id
            ).delete(synchronize_session=False)

            for package in extra_deps:
                pkg = DeploymentPackage(
                    deployment_id=deployment_id,
                    package_name=package,
                )
                db.add(pkg)

            # Update deployment files in database (no local file paths)
            app_file_record = DeploymentFile.get_file(db, deployment_id, "app")
            if app_file_record:
                app_file_record.file_content = modal_code
                app_file_record.file_path = ""  # No persistent local file
            else:
                db.add(DeploymentFile(
                    deployment_id=deployment_id,
                    file_type="app",
                    file_path="",  # No persistent local file
                    file_content=modal_code,
                ))

            original_file_record = DeploymentFile.get_file(db, deployment_id, "original_tools")
            if original_file_record:
                original_file_record.file_content = final_tools_code
                original_file_record.file_path = ""  # No persistent local file
            else:
                db.add(DeploymentFile(
                    deployment_id=deployment_id,
                    file_type="original_tools",
                    file_path="",  # No persistent local file
                    file_content=final_tools_code,
                ))

            # Update tools manifest
            tools_list = _extract_tool_definitions(cleaned_code)
            tools_manifest_record = DeploymentFile.get_file(db, deployment_id, "tools_manifest")
            if tools_manifest_record:
                tools_manifest_record.file_content = json.dumps(tools_list, indent=2)
            else:
                db.add(DeploymentFile(
                    deployment_id=deployment_id,
                    file_type="tools_manifest",
                    file_path="",
                    file_content=json.dumps(tools_list, indent=2),
                ))

            # Log code update event
            DeploymentHistory.log_event(
                db=db,
                deployment_id=deployment_id,
                action="code_updated",
                details={
                    "updated_fields": updated_fields,
                    "redeployed": True,
                    "new_url": deployed_url,
                    "packages": extra_deps,
                }
            )

            security_msg = ""
            if scan_result["severity"] in ["low", "medium"]:
                security_msg = f"\n⚠️  Security Warning ({scan_result['severity']}): {scan_result['explanation']}"

            # Generate Claude Desktop integration config
            mcp_endpoint = f"{deployed_url}/mcp/" if deployed_url else None
            claude_desktop_config = {
                final_server_name: {
                    "command": "npx",
                    "args": [
                        "mcp-remote",
                        mcp_endpoint
                    ]
                }
            } if mcp_endpoint else {}

            config_locations = {
                "macOS": "~/Library/Application Support/Claude/claude_desktop_config.json",
                "Windows": "%APPDATA%/Claude/claude_desktop_config.json",
                "Linux": "~/.config/Claude/claude_desktop_config.json"
            }

            return {
                "success": True,
                "redeployed": True,
                "url": deployed_url,
                "mcp_endpoint": mcp_endpoint,
                "updated_fields": updated_fields,
                "deployment": {
                    "deployment_id": deployment.deployment_id,
                    "app_name": deployment.app_name,
                    "server_name": deployment.server_name,
                    "url": deployment.url,
                    "mcp_endpoint": deployment.mcp_endpoint,
                    "description": deployment.description,
                    "status": deployment.status,
                    "category": deployment.category,
                    "tags": deployment.tags or [],
                    "author": deployment.author,
                    "version": deployment.version,
                    "created_at": deployment.created_at.isoformat() if deployment.created_at else None,
                    "updated_at": deployment.updated_at.isoformat() if deployment.updated_at else None,
                },
                "security_scan": scan_result,
                "claude_desktop_config": claude_desktop_config,
                "config_locations": config_locations,
                "message": f"✅ Successfully updated '{final_server_name}'\n🔗 URL: {deployed_url}{security_msg}\n\n🔌 **Connect to Claude Desktop:**\nAdd this to your claude_desktop_config.json:\n```json\n{json.dumps(claude_desktop_config, indent=2)}\n```"
            }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Deployment timed out after 5 minutes"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _create_deployment_tools() -> List[gr.Interface]:
    """
    Create and return all deployment-related Gradio interfaces.
    Most tools are registered via @gr.api() decorator above.

    Returns:
        List of Gradio interfaces (empty list since tools use @gr.api())
    """
    return []
