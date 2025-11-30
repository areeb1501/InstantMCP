"""
SQLAlchemy ORM Models for MCP Server

Defines database models for deployment management and usage tracking.

FIXES APPLIED:
- DeploymentFile check constraint now includes 'tools_manifest'
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    TIMESTAMP,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func

# Base class for all models
Base = declarative_base()


# ============================================================================
# DEPLOYMENT MODEL
# ============================================================================


class Deployment(Base):
    """
    Main deployment model storing MCP server deployment information.
    """

    __tablename__ = "deployments"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Unique identifiers
    deployment_id = Column(String(255), unique=True, nullable=False, index=True)
    app_name = Column(String(255), unique=True, nullable=False, index=True)
    server_name = Column(String(255), nullable=False)

    # Deployment details
    url = Column(Text, nullable=True)
    mcp_endpoint = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="deployed")

    # Organization and metadata (new fields)
    category = Column(String(100), nullable=True, default="Uncategorized", index=True)
    tags = Column(JSONB, nullable=True, default=[])  # List of tags
    author = Column(String(255), nullable=True, default="Anonymous")
    version = Column(String(50), nullable=True, default="1.0.0")
    documentation = Column(Text, nullable=True)  # Markdown documentation

    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(TIMESTAMP, nullable=True, index=True)  # Soft delete

    # Usage statistics (cached for quick access)
    total_requests = Column(Integer, default=0)
    last_used_at = Column(TIMESTAMP, nullable=True, index=True)
    avg_response_time_ms = Column(Float, nullable=True)

    # Relationships
    packages = relationship(
        "DeploymentPackage",
        back_populates="deployment",
        cascade="all, delete-orphan",
    )
    files = relationship(
        "DeploymentFile",
        back_populates="deployment",
        cascade="all, delete-orphan",
    )
    history = relationship(
        "DeploymentHistory",
        back_populates="deployment",
        cascade="all, delete-orphan",
    )
    usage_events = relationship(
        "UsageEvent",
        back_populates="deployment",
        cascade="all, delete-orphan",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("deployment_id != ''", name="deployments_deployment_id_check"),
        CheckConstraint("app_name != ''", name="deployments_app_name_check"),
        CheckConstraint("server_name != ''", name="deployments_server_name_check"),
    )

    def __repr__(self):
        return f"<Deployment(id={self.id}, deployment_id='{self.deployment_id}', server_name='{self.server_name}')>"

    @property
    def is_deleted(self) -> bool:
        """Check if deployment is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self):
        """Soft delete this deployment."""
        self.deleted_at = datetime.utcnow()
        self.status = "deleted"

    def to_dict(self) -> Dict[str, Any]:
        """Convert deployment to dictionary."""
        return {
            "id": self.id,
            "deployment_id": self.deployment_id,
            "app_name": self.app_name,
            "server_name": self.server_name,
            "url": self.url,
            "mcp_endpoint": self.mcp_endpoint,
            "description": self.description,
            "status": self.status,
            "category": self.category,
            "tags": self.tags or [],
            "author": self.author,
            "version": self.version,
            "documentation": self.documentation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "total_requests": self.total_requests,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "avg_response_time_ms": self.avg_response_time_ms,
            "packages": [pkg.package_name for pkg in self.packages],
        }

    def update_usage_stats(self, duration_ms: float):
        """
        Update usage statistics for this deployment.

        Args:
            duration_ms: Response time in milliseconds
        """
        self.total_requests += 1
        self.last_used_at = datetime.utcnow()

        # Update average response time (moving average)
        if self.avg_response_time_ms is None:
            self.avg_response_time_ms = duration_ms
        else:
            # Weighted average: 90% old average, 10% new value
            self.avg_response_time_ms = (
                0.9 * self.avg_response_time_ms + 0.1 * duration_ms
            )

    @staticmethod
    def get_active_deployments(db: Session) -> List["Deployment"]:
        """Get all active (non-deleted) deployments with status 'deployed'."""
        return (
            db.query(Deployment)
            .filter(Deployment.deleted_at.is_(None))
            .filter(Deployment.status == "deployed")
            .order_by(Deployment.created_at.desc())
            .all()
        )

    @staticmethod
    def get_by_deployment_id(
        db: Session, deployment_id: str, include_deleted: bool = False
    ) -> Optional["Deployment"]:
        """Get deployment by deployment_id."""
        query = db.query(Deployment).filter(
            Deployment.deployment_id == deployment_id
        )
        if not include_deleted:
            query = query.filter(Deployment.deleted_at.is_(None))
        return query.first()

    @staticmethod
    def get_by_app_name(
        db: Session, app_name: str, include_deleted: bool = False
    ) -> Optional["Deployment"]:
        """Get deployment by app_name."""
        query = db.query(Deployment).filter(Deployment.app_name == app_name)
        if not include_deleted:
            query = query.filter(Deployment.deleted_at.is_(None))
        return query.first()


# ============================================================================
# DEPLOYMENT PACKAGE MODEL
# ============================================================================


class DeploymentPackage(Base):
    """
    Model for Python packages required by deployments.
    """

    __tablename__ = "deployment_packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deployment_id = Column(
        String(255),
        ForeignKey("deployments.deployment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    package_name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationship
    deployment = relationship("Deployment", back_populates="packages")

    # Constraints
    __table_args__ = (
        Index("unique_deployment_package", "deployment_id", "package_name", unique=True),
    )

    def __repr__(self):
        return f"<DeploymentPackage(deployment_id='{self.deployment_id}', package='{self.package_name}')>"


# ============================================================================
# DEPLOYMENT FILE MODEL
# ============================================================================


class DeploymentFile(Base):
    """
    Model for storing deployment code files.
    """

    __tablename__ = "deployment_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deployment_id = Column(
        String(255),
        ForeignKey("deployments.deployment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_type = Column(String(50), nullable=False, index=True)  # 'app', 'original_tools', or 'tools_manifest'
    file_path = Column(Text, nullable=True)  # For backward compatibility
    file_content = Column(Text, nullable=True)  # Actual Python code
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationship
    deployment = relationship("Deployment", back_populates="files")

    # ✅ FIX: Updated constraint to include 'tools_manifest'
    __table_args__ = (
        CheckConstraint(
            "file_type IN ('app', 'original_tools', 'tools_manifest')",  # ✅ ADDED tools_manifest
            name="deployment_files_type_check",
        ),
    )

    def __repr__(self):
        return f"<DeploymentFile(deployment_id='{self.deployment_id}', type='{self.file_type}')>"

    @staticmethod
    def get_file(
        db: Session, deployment_id: str, file_type: str
    ) -> Optional["DeploymentFile"]:
        """Get a specific file for a deployment."""
        return (
            db.query(DeploymentFile)
            .filter(
                DeploymentFile.deployment_id == deployment_id,
                DeploymentFile.file_type == file_type,
            )
            .first()
        )


# ============================================================================
# DEPLOYMENT HISTORY MODEL
# ============================================================================


class DeploymentHistory(Base):
    """
    Audit log for deployment lifecycle events.
    """

    __tablename__ = "deployment_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deployment_id = Column(
        String(255),
        ForeignKey("deployments.deployment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = Column(String(50), nullable=False, index=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, index=True)

    # Relationship
    deployment = relationship("Deployment", back_populates="history")

    def __repr__(self):
        return f"<DeploymentHistory(deployment_id='{self.deployment_id}', action='{self.action}')>"

    @staticmethod
    def log_event(
        db: Session,
        deployment_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log a deployment event."""
        event = DeploymentHistory(
            deployment_id=deployment_id,
            action=action,
            details=details or {},
        )
        db.add(event)
        db.flush()
        return event


# ============================================================================
# USAGE EVENT MODEL
# ============================================================================


class UsageEvent(Base):
    """
    Model for tracking deployment usage events and statistics.
    """

    __tablename__ = "usage_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deployment_id = Column(
        String(255),
        ForeignKey("deployments.deployment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Request details
    tool_name = Column(String(255), nullable=True, index=True)
    client_id = Column(String(255), nullable=True, index=True)

    # Performance metrics
    duration_ms = Column(Integer, nullable=True)

    # Status
    success = Column(Boolean, default=True, index=True)
    error_message = Column(Text, nullable=True)

    # Request metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    request_metadata = Column("metadata", JSONB, nullable=True)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow, index=True)

    # Relationship
    deployment = relationship("Deployment", back_populates="usage_events")

    # Composite index for common queries
    __table_args__ = (
        Index("idx_usage_events_deployment_timestamp", "deployment_id", "timestamp"),
    )

    def __repr__(self):
        return f"<UsageEvent(deployment_id='{self.deployment_id}', tool='{self.tool_name}', timestamp='{self.timestamp}')>"

    @staticmethod
    def record_usage(
        db: Session,
        deployment_id: str,
        tool_name: Optional[str] = None,
        client_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "UsageEvent":
        """
        Record a usage event.

        Args:
            db: Database session
            deployment_id: Deployment identifier
            tool_name: Name of tool/function called
            client_id: Client identifier
            duration_ms: Request duration in milliseconds
            success: Whether request succeeded
            error_message: Error message if failed
            metadata: Additional metadata

        Returns:
            UsageEvent: Created usage event
        """
        event = UsageEvent(
            deployment_id=deployment_id,
            tool_name=tool_name,
            client_id=client_id,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            request_metadata=metadata or {},
        )
        db.add(event)
        db.flush()

        # Update deployment statistics
        deployment = Deployment.get_by_deployment_id(db, deployment_id)
        if deployment and duration_ms is not None:
            deployment.update_usage_stats(duration_ms)

        return event

    @staticmethod
    def get_stats(
        db: Session,
        deployment_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a deployment.

        Args:
            db: Database session
            deployment_id: Deployment identifier
            days: Number of days to look back

        Returns:
            dict: Usage statistics
        """
        from sqlalchemy import and_

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Base query for time period
        base_query = db.query(UsageEvent).filter(
            and_(
                UsageEvent.deployment_id == deployment_id,
                UsageEvent.timestamp >= cutoff_date,
            )
        )

        # Total requests
        total_requests = base_query.count()

        # Success rate
        successful_requests = base_query.filter(UsageEvent.success == True).count()
        success_rate = (
            (successful_requests / total_requests * 100) if total_requests > 0 else 0
        )

        # Average response time
        avg_duration = (
            db.query(func.avg(UsageEvent.duration_ms))
            .filter(
                and_(
                    UsageEvent.deployment_id == deployment_id,
                    UsageEvent.timestamp >= cutoff_date,
                    UsageEvent.duration_ms.isnot(None),
                )
            )
            .scalar()
        )

        # Most used tools
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
            .limit(10)
            .all()
        )

        # Client stats
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
            .limit(10)
            .all()
        )

        return {
            "period_days": days,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": total_requests - successful_requests,
            "success_rate_percent": round(success_rate, 2),
            "avg_response_time_ms": round(avg_duration, 2) if avg_duration else None,
            "top_tools": [
                {"tool_name": tool, "count": count} for tool, count in tool_stats
            ],
            "top_clients": [
                {"client_id": client, "count": count} for client, count in client_stats
            ],
        }


# ============================================================================
# Helper Functions
# ============================================================================


def create_all_tables(engine):
    """
    Create all tables in the database.

    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.create_all(engine)
    print("All tables created successfully")


def drop_all_tables(engine):
    """
    Drop all tables from the database.

    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.drop_all(engine)
    print("All tables dropped successfully")
