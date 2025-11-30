"""
Usage Tracking for MCP Server

Provides decorators and utilities for tracking deployment usage statistics.
Tracks request counts, response times, tool usage, and client information.
"""

import time
import functools
from typing import Optional, Callable, Any, Dict
from datetime import datetime

from sqlalchemy.orm import Session

from .database import get_db, db_transaction
from .models import UsageEvent, Deployment


# ============================================================================
# Usage Tracking Decorator
# ============================================================================


def track_usage(
    deployment_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    client_id_getter: Optional[Callable] = None,
):
    """
    Decorator to track usage of MCP server functions.

    Automatically records:
    - Execution time
    - Success/failure status
    - Tool name
    - Client identifier

    Args:
        deployment_id: Deployment ID (can be None if extracted from function args)
        tool_name: Name of the tool/function being tracked
        client_id_getter: Optional function to extract client ID from request

    Example:
        >>> @track_usage(tool_name="get_cat_facts")
        >>> def get_cat_facts(deployment_id: str, count: int = 5):
        >>>     # Function implementation
        >>>     pass

        >>> @track_usage(
        >>>     tool_name="custom_tool",
        >>>     client_id_getter=lambda req: req.headers.get("X-Client-ID")
        >>> )
        >>> def custom_tool(request, deployment_id: str):
        >>>     # Function implementation
        >>>     pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract deployment_id from arguments if not provided
            dep_id = deployment_id
            if dep_id is None:
                # Try to get from kwargs
                dep_id = kwargs.get("deployment_id")
                # Try to get from first positional arg if it's a string
                if dep_id is None and args and isinstance(args[0], str):
                    dep_id = args[0]

            # Extract client_id if getter provided
            client_id = None
            if client_id_getter:
                try:
                    # Try to get client_id from args/kwargs
                    if args:
                        client_id = client_id_getter(args[0])
                    elif kwargs:
                        client_id = client_id_getter(kwargs)
                except Exception:
                    client_id = None

            # Start timing
            start_time = time.time()
            success = True
            error_msg = None
            result = None

            try:
                # Execute the function
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                success = False
                error_msg = str(e)
                raise

            finally:
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)

                # Record usage asynchronously (non-blocking)
                if dep_id:
                    try:
                        record_usage_event(
                            deployment_id=dep_id,
                            tool_name=tool_name or func.__name__,
                            client_id=client_id,
                            duration_ms=duration_ms,
                            success=success,
                            error_message=error_msg,
                        )
                    except Exception as tracking_error:
                        # Don't let tracking errors affect the main function
                        print(f"Warning: Failed to record usage: {tracking_error}")

        return wrapper

    return decorator


# ============================================================================
# Usage Recording Functions
# ============================================================================


def record_usage_event(
    deployment_id: str,
    tool_name: Optional[str] = None,
    client_id: Optional[str] = None,
    duration_ms: Optional[int] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Record a usage event in the database.

    Args:
        deployment_id: Deployment identifier
        tool_name: Name of tool/function called
        client_id: Client identifier
        duration_ms: Request duration in milliseconds
        success: Whether request succeeded
        error_message: Error message if failed
        metadata: Additional metadata

    Returns:
        bool: True if recorded successfully, False otherwise

    Example:
        >>> record_usage_event(
        >>>     deployment_id="deploy-mcp-example-123456",
        >>>     tool_name="get_cat_facts",
        >>>     duration_ms=150,
        >>>     success=True
        >>> )
    """
    try:
        with db_transaction() as db:
            UsageEvent.record_usage(
                db=db,
                deployment_id=deployment_id,
                tool_name=tool_name,
                client_id=client_id,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
                metadata=metadata,
            )
        return True
    except Exception as e:
        print(f"Error recording usage event: {e}")
        return False


def increment_deployment_counter(deployment_id: str, duration_ms: Optional[int] = None):
    """
    Increment deployment usage counter and update statistics.

    This is a lightweight alternative to recording full events.
    Updates total_requests, last_used_at, and avg_response_time_ms.

    Args:
        deployment_id: Deployment identifier
        duration_ms: Optional response time to update average

    Returns:
        bool: True if updated successfully, False otherwise

    Example:
        >>> increment_deployment_counter("deploy-mcp-example-123456", 150)
    """
    try:
        with db_transaction() as db:
            deployment = Deployment.get_by_deployment_id(db, deployment_id)
            if deployment:
                if duration_ms is not None:
                    deployment.update_usage_stats(duration_ms)
                else:
                    deployment.total_requests += 1
                    deployment.last_used_at = datetime.utcnow()
        return True
    except Exception as e:
        print(f"Error incrementing deployment counter: {e}")
        return False


# ============================================================================
# Statistics Retrieval
# ============================================================================


def get_deployment_statistics(
    deployment_id: str,
    days: int = 30,
) -> Optional[Dict[str, Any]]:
    """
    Get usage statistics for a deployment.

    Args:
        deployment_id: Deployment identifier
        days: Number of days to look back

    Returns:
        dict: Usage statistics or None if error

    Example:
        >>> stats = get_deployment_statistics("deploy-mcp-example-123456", days=7)
        >>> print(f"Total requests: {stats['total_requests']}")
        >>> print(f"Success rate: {stats['success_rate_percent']}%")
    """
    try:
        with get_db() as db:
            stats = UsageEvent.get_stats(db, deployment_id, days)
            return stats
    except Exception as e:
        print(f"Error getting deployment statistics: {e}")
        return None


def get_tool_usage_breakdown(
    deployment_id: str,
    days: int = 30,
    limit: int = 10,
) -> Optional[list]:
    """
    Get breakdown of tool usage for a deployment.

    Args:
        deployment_id: Deployment identifier
        days: Number of days to look back
        limit: Maximum number of tools to return

    Returns:
        list: List of dicts with tool_name and count

    Example:
        >>> tools = get_tool_usage_breakdown("deploy-mcp-example-123456")
        >>> for tool in tools:
        >>>     print(f"{tool['tool_name']}: {tool['count']} requests")
    """
    try:
        from sqlalchemy import and_, func
        from datetime import datetime, timedelta

        with get_db() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            tool_stats = (
                db.query(
                    UsageEvent.tool_name,
                    func.count(UsageEvent.id).label("count"),
                )
                .filter(
                    and_(
                        UsageEvent.deployment_id == deployment_id,
                        UsageEvent.timestamp >= cutoff_date,
                        UsageEvent.tool_name.isnot(None),
                    )
                )
                .group_by(UsageEvent.tool_name)
                .order_by(func.count(UsageEvent.id).desc())
                .limit(limit)
                .all()
            )

            return [
                {"tool_name": tool, "count": count}
                for tool, count in tool_stats
            ]
    except Exception as e:
        print(f"Error getting tool usage breakdown: {e}")
        return None


def get_usage_timeline(
    deployment_id: str,
    days: int = 7,
    granularity: str = "day",
) -> Optional[list]:
    """
    Get usage timeline for a deployment.

    Args:
        deployment_id: Deployment identifier
        days: Number of days to look back
        granularity: 'hour' or 'day'

    Returns:
        list: List of dicts with timestamp and count

    Example:
        >>> timeline = get_usage_timeline("deploy-mcp-example-123456", days=7)
        >>> for entry in timeline:
        >>>     print(f"{entry['date']}: {entry['requests']} requests")
    """
    try:
        from sqlalchemy import and_, func
        from datetime import datetime, timedelta

        with get_db() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Choose date truncation based on granularity
            if granularity == "hour":
                time_bucket = func.date_trunc("hour", UsageEvent.timestamp)
            else:
                time_bucket = func.date_trunc("day", UsageEvent.timestamp)

            timeline_data = (
                db.query(
                    time_bucket.label("time_bucket"),
                    func.count(UsageEvent.id).label("count"),
                )
                .filter(
                    and_(
                        UsageEvent.deployment_id == deployment_id,
                        UsageEvent.timestamp >= cutoff_date,
                    )
                )
                .group_by(time_bucket)
                .order_by(time_bucket)
                .all()
            )

            return [
                {
                    "timestamp": bucket.isoformat() if bucket else None,
                    "requests": count,
                }
                for bucket, count in timeline_data
            ]
    except Exception as e:
        print(f"Error getting usage timeline: {e}")
        return None


def get_client_statistics(
    deployment_id: str,
    days: int = 30,
    limit: int = 10,
) -> Optional[list]:
    """
    Get client usage statistics for a deployment.

    Args:
        deployment_id: Deployment identifier
        days: Number of days to look back
        limit: Maximum number of clients to return

    Returns:
        list: List of dicts with client_id and count

    Example:
        >>> clients = get_client_statistics("deploy-mcp-example-123456")
        >>> for client in clients:
        >>>     print(f"Client {client['client_id']}: {client['count']} requests")
    """
    try:
        from sqlalchemy import and_, func
        from datetime import datetime, timedelta

        with get_db() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            client_stats = (
                db.query(
                    UsageEvent.client_id,
                    func.count(UsageEvent.id).label("count"),
                )
                .filter(
                    and_(
                        UsageEvent.deployment_id == deployment_id,
                        UsageEvent.timestamp >= cutoff_date,
                        UsageEvent.client_id.isnot(None),
                    )
                )
                .group_by(UsageEvent.client_id)
                .order_by(func.count(UsageEvent.id).desc())
                .limit(limit)
                .all()
            )

            return [
                {"client_id": client, "count": count}
                for client, count in client_stats
            ]
    except Exception as e:
        print(f"Error getting client statistics: {e}")
        return None


# ============================================================================
# Utility Functions
# ============================================================================


def get_all_deployments_stats() -> Optional[list]:
    """
    Get quick statistics for all active deployments.

    Returns:
        list: List of dicts with deployment info and stats

    Example:
        >>> all_stats = get_all_deployments_stats()
        >>> for deployment in all_stats:
        >>>     print(f"{deployment['server_name']}: {deployment['total_requests']} requests")
    """
    try:
        with get_db() as db:
            deployments = Deployment.get_active_deployments(db)
            return [
                {
                    "deployment_id": dep.deployment_id,
                    "server_name": dep.server_name,
                    "total_requests": dep.total_requests or 0,
                    "last_used_at": dep.last_used_at.isoformat() if dep.last_used_at else None,
                    "avg_response_time_ms": dep.avg_response_time_ms,
                    "status": dep.status,
                }
                for dep in deployments
            ]
    except Exception as e:
        print(f"Error getting all deployments stats: {e}")
        return None
