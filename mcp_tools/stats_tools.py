"""
Statistics Tools Module

Gradio-based MCP tools for statistics and analytics.
"""

import gradio as gr
from typing import List
from utils.usage_tracker import (
    get_deployment_statistics,
    get_tool_usage_breakdown,
    get_usage_timeline,
    get_client_statistics,
    get_all_deployments_stats,
)


def get_deployment_stats(deployment_id: str, days: int = 30) -> dict:
    """
    Get usage statistics for a specific deployment.

    Args:
        deployment_id: The deployment ID to get stats for
        days: Number of days to look back (default: 30)

    Returns:
        dict with usage statistics
    """
    try:
        stats = get_deployment_statistics(deployment_id, days)
        if stats is None:
            return {
                "success": False,
                "error": f"Failed to retrieve statistics for {deployment_id}"
            }
        return {
            "success": True,
            "deployment_id": deployment_id,
            "stats": stats
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_tool_usage(deployment_id: str, days: int = 30, limit: int = 10) -> dict:
    """
    Get breakdown of tool usage for a deployment.

    Args:
        deployment_id: The deployment ID
        days: Number of days to look back (default: 30)
        limit: Maximum number of tools to return (default: 10)

    Returns:
        dict with tool usage breakdown
    """
    try:
        tools = get_tool_usage_breakdown(deployment_id, days, limit)
        if tools is None:
            return {
                "success": False,
                "error": f"Failed to retrieve tool usage for {deployment_id}"
            }
        return {
            "success": True,
            "deployment_id": deployment_id,
            "period_days": days,
            "tools": tools
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_all_stats_summary() -> dict:
    """
    Get quick statistics summary for all deployments.

    Returns:
        dict with all deployment statistics
    """
    try:
        all_stats = get_all_deployments_stats()
        if all_stats is None:
            return {
                "success": False,
                "error": "Failed to retrieve deployment statistics"
            }
        return {
            "success": True,
            "total_deployments": len(all_stats),
            "deployments": all_stats
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _create_stats_tools() -> List[gr.Interface]:
    """
    Create and return all statistics-related Gradio interfaces.
    Tools are registered via @gr.api() decorator above.

    Returns:
        List of Gradio interfaces (empty - using @gr.api())
    """
    return []
