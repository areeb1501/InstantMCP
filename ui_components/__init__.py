"""
UI Components Module

This module contains all Gradio UI components for the web interface.
"""

from .admin_panel import create_admin_panel
from .code_editor import create_code_editor
from .stats_dashboard import create_stats_dashboard
from .log_viewer import create_log_viewer

__all__ = [
    'create_admin_panel',
    'create_code_editor',
    'create_stats_dashboard',
    'create_log_viewer',
]
