import os
from typing import List, Optional


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


# PUBLIC_INTERFACE
def get_cors_allow_origins() -> List[str]:
    """Get CORS allow-origins list from env.

    Env:
        CORS_ALLOW_ORIGINS:
            Comma-separated list of allowed origins. Example:
            "http://localhost:3000,https://myapp.example.com"

    Returns:
        List of origins. Defaults to ["*"] if not set.
    """
    raw = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    if not raw:
        return ["*"]
    origins = _split_csv(raw)
    return origins or ["*"]


# PUBLIC_INTERFACE
def get_payment_webhook_secret() -> str:
    """Return the shared secret used to validate mock payment webhook calls.

    Env:
        PAYMENT_WEBHOOK_SECRET: shared secret string.

    Notes:
        In production, always set this. For local development, a default is provided
        to keep the template runnable.
    """
    return os.getenv("PAYMENT_WEBHOOK_SECRET", "dev_webhook_secret")


# PUBLIC_INTERFACE
def get_site_url() -> Optional[str]:
    """Return SITE_URL (used for redirect/callback URLs if needed).

    Env:
        SITE_URL: base public URL for this deployment (frontend URL typically).
    """
    v = os.getenv("SITE_URL")
    return v.strip() if v else None
