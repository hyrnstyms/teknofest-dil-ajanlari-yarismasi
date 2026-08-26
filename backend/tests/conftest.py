"""Shared test configuration for persistent analysis storage."""

import os
import tempfile
from pathlib import Path


# Unit/API tests use one process-local file database. PostgreSQL compatibility
# is exercised separately with docker-compose in the acceptance workflow.
_test_database = Path(tempfile.gettempdir()) / f"kamuai-pytest-{os.getpid()}.sqlite3"
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_APP_DATABASE_URL", f"sqlite:///{_test_database}"
)
