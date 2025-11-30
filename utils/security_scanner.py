#!/usr/bin/env python3
"""
Security Scanner Module - AI-powered vulnerability detection for MCP deployments

Uses Nebius AI to analyze Python code for security vulnerabilities before deployment.
Focuses on real threats: code injection, malicious behavior, resource abuse.
"""

import os
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional
from openai import OpenAI


# Cache for security scan results (code_hash -> scan_result)
# Avoids re-scanning identical code
_scan_cache = {}
_cache_expiry = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def _get_code_hash(code: str) -> str:
    """Generate SHA256 hash of code for caching"""
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def _get_cached_scan(code_hash: str) -> Optional[dict]:
    """Retrieve cached scan result if still valid"""
    if code_hash in _scan_cache:
        expiry = _cache_expiry.get(code_hash)
        if expiry and datetime.now() < expiry:
            return _scan_cache[code_hash]
        else:
            # Expired, remove from cache
            _scan_cache.pop(code_hash, None)
            _cache_expiry.pop(code_hash, None)
    return None


def _cache_scan_result(code_hash: str, result: dict):
    """Cache scan result with TTL"""
    _scan_cache[code_hash] = result
    _cache_expiry[code_hash] = datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)


def _map_severity(malicious_type: str) -> str:
    """
    Map malicious type to severity level.

    Critical: Immediate threat to system/data
    High: Significant vulnerability
    Medium: Potential issue
    Low: Minor concern
    Safe: No issues
    """
    severity_map = {
        # Critical threats
        "ransomware": "critical",
        "backdoor": "critical",
        "remote_access_tool": "critical",
        "credential_harvesting": "critical",

        # High severity
        "sql_injection": "high",
        "command_injection": "high",
        "ddos_script": "high",

        # Medium severity
        "obfuscated_suspicious": "medium",
        "trojan": "medium",
        "keylogger": "medium",

        # Low severity
        "other": "low",
        "virus": "low",
        "worm": "low",

        # Safe
        "none": "safe"
    }

    return severity_map.get(malicious_type.lower(), "medium")


def _build_security_prompt(code: str, context: dict) -> str:
    """
    Build comprehensive security analysis prompt.

    Focuses on real threats while ignoring false positives like hardcoded keys
    (since all deployed code is public on Modal.com).
    """
    server_name = context.get("server_name", "Unknown")
    packages = context.get("packages", [])
    description = context.get("description", "")

    prompt = f"""You are an expert security analyst reviewing Python code for MCP server deployments on Modal.com.

**IMPORTANT CONTEXT:**
- All deployed code is PUBLIC and visible to anyone
- Hardcoded API keys/credentials are NOT a security threat for this platform (though bad practice)
- Focus on vulnerabilities that could harm the platform or users

**Code to Analyze:**
```python
{code}
```

**Deployment Context:**
- Server Name: {server_name}
- Packages: {', '.join(packages) if packages else 'None'}
- Description: {description}

**Check for REAL THREATS (flag these):**

1. **Code Injection Vulnerabilities:**
   - eval() or exec() with user input
   - subprocess calls with unsanitized input (especially shell=True)
   - SQL queries using string concatenation
   - Dynamic imports from user input

2. **Malicious Network Behavior:**
   - Data exfiltration to suspicious domains
   - Command & Control (C2) communication patterns
   - Cryptocurrency mining
   - Unusual outbound connections to non-standard ports

3. **Resource Abuse:**
   - Infinite loops or recursive calls
   - Memory exhaustion attacks
   - CPU intensive operations without limits
   - Denial of Service patterns

4. **Destructive Operations:**
   - Attempts to escape sandbox/container
   - System file manipulation
   - Process manipulation (killing other processes)
   - Privilege escalation attempts

5. **Malicious Packages:**
   - Known malicious PyPI packages
   - Typosquatting package names
   - Packages with known CVEs

**DO NOT FLAG (these are acceptable):**
- Hardcoded API keys, passwords, or tokens (code is public anyway)
- Legitimate external API calls (OpenAI, Anthropic, etc.)
- Normal file operations (reading/writing files in sandbox)
- Standard web requests to known services
- Environment variable usage

**Provide detailed analysis with specific line references if issues found.**
"""

    return prompt


def scan_code_for_security(code: str, context: dict) -> dict:
    """
    Scan Python code for security vulnerabilities using Nebius AI.

    Args:
        code: The Python code to scan
        context: Dictionary with deployment context:
            - server_name: Name of the server
            - packages: List of pip packages
            - description: Server description
            - deployment_id: Optional deployment ID

    Returns:
        dict with:
        - scan_completed: bool (whether scan finished)
        - is_safe: bool (whether code is safe to deploy)
        - severity: str ("safe", "low", "medium", "high", "critical")
        - malicious_type: str (type of threat or "none")
        - explanation: str (human-readable explanation)
        - reasoning_steps: list[str] (AI's reasoning process)
        - issues: list[dict] (specific issues found)
        - recommendation: str (what to do)
        - scanned_at: str (ISO timestamp)
        - cached: bool (whether result came from cache)
    """

    # Check if scanning is enabled
    if os.getenv("SECURITY_SCANNING_ENABLED", "true").lower() != "true":
        return {
            "scan_completed": False,
            "is_safe": True,
            "severity": "safe",
            "malicious_type": "none",
            "explanation": "Security scanning is disabled",
            "reasoning_steps": ["Security scanning disabled via SECURITY_SCANNING_ENABLED=false"],
            "issues": [],
            "recommendation": "Allow (scanning disabled)",
            "scanned_at": datetime.now().isoformat(),
            "cached": False
        }

    # Check cache first
    code_hash = _get_code_hash(code)
    cached_result = _get_cached_scan(code_hash)
    if cached_result:
        cached_result["cached"] = True
        return cached_result

    # Get API key
    api_key = os.getenv("NEBIUS_API_KEY")
    if not api_key:
        # Fall back to warning mode if no API key
        return {
            "scan_completed": False,
            "is_safe": True,
            "severity": "safe",
            "malicious_type": "none",
            "explanation": "NEBIUS_API_KEY not configured - security scanning unavailable",
            "reasoning_steps": ["No API key found in environment"],
            "issues": [],
            "recommendation": "Warn (no API key)",
            "scanned_at": datetime.now().isoformat(),
            "cached": False
        }

    try:
        # Initialize Nebius client (OpenAI-compatible)
        client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=api_key
        )

        # Build security analysis prompt
        prompt = _build_security_prompt(code, context)

        # Call Nebius API with structured JSON schema
        response = client.chat.completions.create(
            model="Qwen/Qwen3-32B-fast",
            temperature=0.6,
            top_p=0.95,
            timeout=30.0,  # 30 second timeout
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "security_analysis_schema",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "reasoning_steps": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "The reasoning steps leading to the final conclusion."
                            },
                            "is_malicious": {
                                "type": "boolean",
                                "description": "Indicates whether the provided code or content is malicious (true) or safe/non-malicious (false)."
                            },
                            "malicious_type": {
                                "type": "string",
                                "enum": [
                                    "none",
                                    "virus",
                                    "worm",
                                    "ransomware",
                                    "trojan",
                                    "keylogger",
                                    "backdoor",
                                    "remote_access_tool",
                                    "sql_injection",
                                    "command_injection",
                                    "ddos_script",
                                    "credential_harvesting",
                                    "obfuscated_suspicious",
                                    "other"
                                ],
                                "description": "If malicious, classify the type. Use 'none' when code is safe."
                            },
                            "explanation": {
                                "type": "string",
                                "description": "A short, safe explanation of why the code is considered malicious or not, without including harmful details."
                            },
                            "answer": {
                                "type": "string",
                                "description": "The final answer, taking all reasoning steps into account."
                            }
                        },
                        "required": [
                            "reasoning_steps",
                            "is_malicious",
                            "malicious_type",
                            "explanation",
                            "answer"
                        ],
                        "additionalProperties": False
                    }
                }
            },
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Parse response
        response_content = response.choices[0].message.content
        scan_data = json.loads(response_content)

        # Map to our format
        severity = _map_severity(scan_data["malicious_type"])
        is_safe = not scan_data["is_malicious"]

        # Determine recommendation
        if severity in ["critical", "high"]:
            recommendation = "Block deployment"
        elif severity in ["medium", "low"]:
            recommendation = "Warn and allow"
        else:
            recommendation = "Allow"

        # Build issues list
        issues = []
        if scan_data["is_malicious"]:
            issues.append({
                "type": scan_data["malicious_type"],
                "severity": severity,
                "description": scan_data["explanation"]
            })

        result = {
            "scan_completed": True,
            "is_safe": is_safe,
            "severity": severity,
            "malicious_type": scan_data["malicious_type"],
            "explanation": scan_data["explanation"],
            "reasoning_steps": scan_data["reasoning_steps"],
            "issues": issues,
            "recommendation": recommendation,
            "scanned_at": datetime.now().isoformat(),
            "cached": False,
            "raw_answer": scan_data.get("answer", "")
        }

        # Cache the result
        _cache_scan_result(code_hash, result)

        return result

    except Exception as e:
        # On error, fall back to warning mode (allow deployment with warning)
        error_msg = str(e)

        return {
            "scan_completed": False,
            "is_safe": True,  # Allow on error
            "severity": "safe",
            "malicious_type": "none",
            "explanation": f"Security scan failed: {error_msg}",
            "reasoning_steps": [f"Error during scan: {error_msg}"],
            "issues": [],
            "recommendation": "Warn (scan failed)",
            "scanned_at": datetime.now().isoformat(),
            "cached": False,
            "error": error_msg
        }


def clear_scan_cache():
    """Clear the security scan cache (useful for testing)"""
    _scan_cache.clear()
    _cache_expiry.clear()
