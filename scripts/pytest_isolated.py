from __future__ import annotations

import os
import sys

# The package owns its test environment; globally installed pytest plugins must
# not change timings, fixtures or shutdown behaviour.
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

import pytest  # noqa: E402


def main() -> None:
    code = int(pytest.main(sys.argv[1:]))
    sys.stdout.flush()
    sys.stderr.flush()
    # Some third-party libraries register interpreter shutdown handlers that
    # can delay a completed certification. The isolated child has no state to
    # preserve after pytest has returned.
    os._exit(code)


if __name__ == "__main__":
    main()
