from __future__ import annotations

PUBLIC_RESULT_PREFIX = "/diagnostico/gracias/"
PUBLIC_RESULT_CANONICAL_PATH = "/diagnostico/gracias/:token"


def is_public_result_path(path: str) -> bool:
    """Return whether a path belongs to the token-addressed public result surface."""
    return path.startswith(PUBLIC_RESULT_PREFIX)


def privacy_safe_path(path: str) -> str:
    """Redact capability-bearing path segments before logs or metric labels."""
    if is_public_result_path(path):
        return PUBLIC_RESULT_CANONICAL_PATH
    return path
