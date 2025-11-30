"""
Database Connection Management for MCP Server

This module handles PostgreSQL database connections using SQLAlchemy.
Provides session management, connection pooling, and transaction handling.
"""

import os
import time
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

# ============================================================================
# Configuration
# ============================================================================

# Get database URL from environment variable
# IMPORTANT: DATABASE_URL must be set in environment - no default provided for security
DATABASE_URL = os.getenv("DATABASE_URL")

# Connection pool configuration
POOL_SIZE = 5  # Number of connections to keep in the pool
MAX_OVERFLOW = 10  # Maximum number of connections that can be created beyond pool_size
POOL_TIMEOUT = 30  # Seconds to wait for connection from pool
POOL_RECYCLE = 3600  # Recycle connections after 1 hour

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# ============================================================================
# Engine Creation (Lazy Initialization)
# ============================================================================

# Global engine and session factory - initialized lazily
_engine: Engine = None
_SessionLocal = None


def _get_engine() -> Engine:
    """
    Get or create the database engine (lazy initialization).
    
    Returns:
        Engine: SQLAlchemy engine instance
        
    Raises:
        ValueError: If DATABASE_URL is not set
    """
    global _engine
    
    if _engine is not None:
        return _engine
    
    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Please set it to your PostgreSQL connection string."
        )
    
    # Create engine with connection pooling
    _engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_recycle=POOL_RECYCLE,
        pool_pre_ping=True,  # Test connections before using them
        echo=False,  # Set to True for SQL query logging (debugging)
    )
    
    # Add connection event listeners
    @event.listens_for(_engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Event listener for new connections."""
        pass
    
    @event.listens_for(_engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Event listener for connection checkout from pool."""
        pass
    
    return _engine


def _get_session_factory():
    """Get or create the session factory (lazy initialization)."""
    global _SessionLocal
    
    if _SessionLocal is not None:
        return _SessionLocal
    
    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_get_engine(),
    )
    return _SessionLocal


# Legacy compatibility - these now use lazy initialization
@property
def engine():
    """Lazy engine property for backward compatibility."""
    return _get_engine()


def create_db_engine() -> Engine:
    """
    Create or get SQLAlchemy engine with connection pooling.
    
    Returns:
        Engine: SQLAlchemy engine instance
        
    Raises:
        ValueError: If DATABASE_URL is not set
    """
    return _get_engine()


# Backward compatible SessionLocal - use get_session_factory() for new code
class SessionLocalProxy:
    """Proxy class for lazy SessionLocal initialization."""
    
    def __call__(self):
        return _get_session_factory()()


SessionLocal = SessionLocalProxy()

# ============================================================================
# Session Management
# ============================================================================


def get_db_session() -> Session:
    """
    Get a new database session.

    Returns:
        Session: SQLAlchemy session instance

    Example:
        >>> session = get_db_session()
        >>> try:
        >>>     # Use session
        >>>     session.commit()
        >>> finally:
        >>>     session.close()
    """
    return SessionLocal()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Automatically handles session lifecycle and rollback on errors.

    Yields:
        Session: SQLAlchemy session instance

    Example:
        >>> with get_db() as db:
        >>>     deployment = db.query(Deployment).first()
        >>>     db.commit()
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def db_transaction() -> Generator[Session, None, None]:
    """
    Context manager for database transactions with automatic commit/rollback.

    The transaction is automatically committed if no exception occurs,
    and rolled back if an exception is raised.

    Yields:
        Session: SQLAlchemy session instance

    Example:
        >>> with db_transaction() as db:
        >>>     deployment = Deployment(...)
        >>>     db.add(deployment)
        >>>     # Automatically committed on successful exit
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ============================================================================
# Retry Logic
# ============================================================================


def execute_with_retry(func, *args, max_retries=MAX_RETRIES, **kwargs):
    """
    Execute a database operation with retry logic.

    Retries the operation if it fails due to connection issues.

    Args:
        func: Function to execute
        *args: Positional arguments for func
        max_retries: Maximum number of retry attempts
        **kwargs: Keyword arguments for func

    Returns:
        Result of func execution

    Raises:
        Exception: If all retry attempts fail

    Example:
        >>> result = execute_with_retry(
        >>>     lambda: db.query(Deployment).all()
        >>> )
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except OperationalError as e:
            last_exception = e
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                continue
            raise
        except SQLAlchemyError:
            raise

    # If we get here, all retries failed
    if last_exception:
        raise last_exception


# ============================================================================
# Health Check
# ============================================================================


def check_database_connection() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        bool: True if connection is successful, False otherwise

    Example:
        >>> if check_database_connection():
        >>>     print("Database is connected")
        >>> else:
        >>>     print("Database connection failed")
    """
    try:
        with get_db() as db:
            # Execute a simple query to test connection
            db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection check failed: {e}")
        return False


def get_database_info() -> dict:
    """
    Get database connection information.

    Returns:
        dict: Database connection details

    Example:
        >>> info = get_database_info()
        >>> print(f"Connected to: {info['database']}")
    """
    try:
        with get_db() as db:
            result = db.execute(
                text("""
                SELECT
                    current_database() as database,
                    current_user as user,
                    version() as version,
                    inet_server_addr() as host,
                    inet_server_port() as port
                """)
            ).first()

            return {
                "database": result[0],
                "user": result[1],
                "version": result[2],
                "host": result[3],
                "port": result[4],
                "connected": True,
            }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }


# ============================================================================
# Cleanup
# ============================================================================


def close_database_connections():
    """
    Close all database connections and dispose of the engine.

    Call this when shutting down the application.

    Example:
        >>> close_database_connections()
    """
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None
        print("Database connections closed")


# ============================================================================
# Initialization
# ============================================================================

if __name__ == "__main__":
    # Test database connection
    print("Testing database connection...")
    print("-" * 60)

    if check_database_connection():
        print("✓ Database connection successful!")
        print()
        info = get_database_info()
        print("Database Information:")
        print(f"  Database: {info.get('database', 'N/A')}")
        print(f"  User: {info.get('user', 'N/A')}")
        print(f"  Host: {info.get('host', 'N/A')}")
        print(f"  Port: {info.get('port', 'N/A')}")
        print()
        print(f"  PostgreSQL Version:")
        version = info.get('version', 'N/A')
        # Print first line of version (can be long)
        print(f"    {version.split(',')[0] if version else 'N/A'}")
    else:
        print("✗ Database connection failed!")
        print()
        print("Please check:")
        print("  1. DATABASE_URL environment variable is set correctly")
        print("  2. PostgreSQL server is running")
        print("  3. Network connectivity to database")
        print("  4. Database credentials are correct")

    print("-" * 60)
