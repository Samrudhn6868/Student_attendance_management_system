"""SAS-96: Integration script to register bunk allowance blueprint.

This script should be imported in main.py to register the bunk allowance API.

Functions:
    register_bunk_allowance_blueprint: Register API blueprint with Flask app
    init_bunk_allowance_tables: Initialize database tables
"""

from typing import Any
from flask import Flask


def register_bunk_allowance_blueprint(app: Flask) -> None:
    """Register the bunk allowance blueprint with the Flask app.

    Args:
        app: Flask application instance

    Returns:
        None
    """
    try:
        from bunk_allowance_api import bunk_allowance_bp
        app.register_blueprint(bunk_allowance_bp)
        print("✓ Bunk Allowance API registered successfully")
    except ImportError as e:
        print(f"Warning: Could not import bunk_allowance_api: {e}")
    except Exception as e:
        print(f"Error registering bunk allowance blueprint: {e}")


def init_bunk_allowance_tables(db: Any) -> None:
    """Initialize bunk allowance database tables.

    Args:
        db: SQLAlchemy database instance

    Returns:
        None
    """
    try:
        from bunk_allowance_models import CourseConfig, StudentBunkAllowance
        # Tables will be created automatically by db.create_all()
        print("✓ Bunk Allowance models loaded successfully")
    except ImportError as e:
        print(f"Warning: Could not import bunk_allowance_models: {e}")
    except Exception as e:
        print(f"Error loading bunk allowance models: {e}")
