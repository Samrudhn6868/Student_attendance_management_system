"""
SAS-96: Bunk Allowance Feature - Quick Integration
===================================================

Add this single line to the end of your src/main.py (before if __name__ == '__main__'):

    from bunk_allowance_quick_setup import setup_bunk_allowance
    setup_bunk_allowance(app, db)

Or manually add:

    from bunk_allowance_api import bunk_allowance_bp
    app.register_blueprint(bunk_allowance_bp)

Then run:
    python scripts/migrate_bunk_allowance.py
"""

def setup_bunk_allowance(app, db):
    """One-line setup for bunk allowance feature.
    
    Call this function from main.py to automatically:
    - Import necessary models
    - Register API blueprint
    - Initialize database tables
    
    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
    
    Usage in main.py:
        from bunk_allowance_quick_setup import setup_bunk_allowance
        setup_bunk_allowance(app, db)
    """
    try:
        # Import models to ensure tables are created
        from bunk_allowance_models import CourseConfig, StudentBunkAllowance
        
        # Import and register blueprint
        from bunk_allowance_api import bunk_allowance_bp
        
        # Register blueprint if not already registered
        if not any(bp.name == 'bunk_allowance' for bp in app.blueprints.values()):
            app.register_blueprint(bunk_allowance_bp)
            print("✓ Bunk Allowance API registered at /api/bunk-allowance")
        
        # Create tables if they don't exist
        with app.app_context():
            db.create_all()
        
        print("✓ Bunk Allowance feature initialized successfully")
        print("  Run 'python scripts/migrate_bunk_allowance.py' for setup")
        
        return True
        
    except ImportError as e:
        print(f"⚠ Warning: Could not setup bunk allowance feature: {e}")
        print("  This is optional and won't affect other features")
        return False
    except Exception as e:
        print(f"⚠ Error setting up bunk allowance: {e}")
        return False


if __name__ == '__main__':
    print(__doc__)
