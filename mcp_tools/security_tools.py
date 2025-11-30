"""
Security Tools Module

Gradio-based MCP tools for security scanning.
"""

import gradio as gr
from typing import List
import re


def scan_deployment_security(
    mcp_tools_code: str,
    server_name: str = "Unknown",
    extra_pip_packages: str = "",
    description: str = ""
) -> dict:
    """
    Manually scan MCP code for security vulnerabilities without deploying.

    Use this tool to check code for security issues before deploying or updating.
    The scan uses AI to detect:
    - Code injection vulnerabilities (SQL, command, etc.)
    - Malicious network behavior
    - Resource abuse patterns
    - Destructive operations
    - Known malicious packages

    Args:
        mcp_tools_code: Python code defining your MCP tools
        server_name: Name for context (default: "Unknown")
        extra_pip_packages: Comma-separated list of additional packages
        description: Optional description for context

    Returns:
        dict with scan results and recommendations
    """
    try:
        # Convert comma-separated packages to list
        extra_pip_packages_list = [p.strip() for p in extra_pip_packages.split(",")] if extra_pip_packages else []

        # Extract imports
        def _extract_imports_and_code_local(user_code: str) -> tuple[list[str], str]:
            """Extract import statements"""
            lines = user_code.strip().split('\n')
            imports = []
            code_lines = []

            for line in lines:
                stripped = line.strip()
                if stripped.startswith('import ') or stripped.startswith('from '):
                    if stripped.startswith('from '):
                        match = re.match(r'from\s+(\w+)', stripped)
                        if match:
                            imports.append(match.group(1))
                    else:
                        match = re.match(r'import\s+(\w+)', stripped)
                        if match:
                            imports.append(match.group(1))
                code_lines.append(line)

            return imports, '\n'.join(code_lines)

        detected_imports, cleaned_code = _extract_imports_and_code_local(mcp_tools_code)
        all_packages = list(set(detected_imports + extra_pip_packages_list))

        # Filter out standard library packages
        stdlib = {'os', 'sys', 'json', 're', 'datetime', 'time', 'typing', 'pathlib',
                  'collections', 'functools', 'itertools', 'math', 'random', 'string',
                  'hashlib', 'base64', 'urllib', 'zoneinfo', 'asyncio'}
        extra_deps = [pkg for pkg in all_packages if pkg.lower() not in stdlib]

        # Perform security scan
        from utils.security_scanner import scan_code_for_security

        scan_result = scan_code_for_security(
            code=cleaned_code,
            context={
                "server_name": server_name,
                "packages": extra_deps,
                "description": description
            }
        )

        # Add helpful interpretation
        if scan_result["is_safe"]:
            scan_result["interpretation"] = "✅ Code appears safe to deploy"
        elif scan_result["severity"] in ["critical", "high"]:
            scan_result["interpretation"] = f"🚫 {scan_result['severity'].upper()} severity issues - deployment would be blocked"
        else:
            scan_result["interpretation"] = f"⚠️  {scan_result['severity'].upper()} severity issues - deployment would proceed with warnings"

        return scan_result

    except Exception as e:
        return {
            "success": False,
            "error": f"Security scan failed: {str(e)}",
            "scan_completed": False,
            "is_safe": None
        }


def _create_security_tools() -> List[gr.Interface]:
    """
    Create and return all security-related Gradio interfaces.
    Tools are registered via @gr.api() decorator above.

    Returns:
        List of Gradio interfaces (empty - using @gr.api())
    """
    return []
