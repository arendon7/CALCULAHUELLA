from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path

# Configure an isolated runtime before any test module imports app.config/database.
_TEST_INSTANCE = Path(tempfile.mkdtemp(prefix="cth_pytest_"))
os.environ["INSTANCE_DIR"] = str(_TEST_INSTANCE)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_INSTANCE / 'calculatuhuella.db'}"
os.environ["APP_ENV"] = "local"
os.environ["SEED_DEMO"] = "1"
os.environ["SCHEDULER_ENABLED"] = "0"
os.environ["STRUCTURED_LOGGING"] = "1"
os.environ["PBKDF2_ITERATIONS"] = "10000"


def _cleanup() -> None:
    shutil.rmtree(_TEST_INSTANCE, ignore_errors=True)


atexit.register(_cleanup)
