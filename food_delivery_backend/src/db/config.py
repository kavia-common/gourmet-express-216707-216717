import os
from pathlib import Path
from typing import Optional

DEFAULT_DB_CONNECTION_TXT_CANDIDATES = [
    # Typical workspace-relative paths in this multi-container setup
    Path("gourmet-express-216707-216718/database/db_connection.txt"),
    Path("../gourmet-express-216707-216718/database/db_connection.txt"),
    Path("../../gourmet-express-216707-216718/database/db_connection.txt"),
    # Sometimes copied next to backend container root
    Path("db_connection.txt"),
]


def _parse_db_connection_txt(text: str) -> Optional[str]:
    """
    Parse db_connection.txt content.

    The database container usually provides a single line like:
      'psql postgresql://user:pass@host:port/dbname'

    Returns the URL string if found, else None.
    """
    raw = text.strip()
    if not raw:
        return None

    # Accept either "psql <url>" or direct "<url>"
    parts = raw.split()
    if len(parts) == 1:
        candidate = parts[0]
    else:
        # If first token is 'psql', assume second token is the URL
        if parts[0].lower() == "psql" and len(parts) >= 2:
            candidate = parts[1]
        else:
            # Try to find the first token that looks like a postgres URL
            candidate = next((p for p in parts if p.startswith("postgresql://")), None)

    if not candidate:
        return None

    if candidate.startswith("postgresql://") or candidate.startswith("postgres://"):
        return candidate

    return None


def _try_read_first_existing(paths: list[Path]) -> Optional[str]:
    for p in paths:
        try:
            if p.is_file():
                return p.read_text(encoding="utf-8")
        except OSError:
            continue
    return None


# PUBLIC_INTERFACE
def get_database_url() -> str:
    """Return the database connection URL from env DATABASE_URL, else db_connection.txt fallback.

    Precedence:
    1) DATABASE_URL environment variable
    2) First readable db_connection.txt among known candidate paths

    Raises:
        RuntimeError: if no database URL can be determined.
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    text = _try_read_first_existing(DEFAULT_DB_CONNECTION_TXT_CANDIDATES)
    if text:
        parsed = _parse_db_connection_txt(text)
        if parsed:
            return parsed

    raise RuntimeError(
        "DATABASE_URL is not set and db_connection.txt could not be read/parsed. "
        "Set DATABASE_URL in the backend environment or ensure db_connection.txt is available."
    )
