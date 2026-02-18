"""
Shared dependencies for the FastAPI backend.
Provides a single LeadsDatabase instance across all route modules.
"""

from models import LeadsDatabase

# Single shared database instance for the entire backend
_db = LeadsDatabase()


def get_db() -> LeadsDatabase:
    """Get the shared database instance."""
    return _db
