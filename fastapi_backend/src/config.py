"""
Configuration module for the FastAPI backend.

This module centralizes environment-based configuration, including optional
Supabase settings. Values are loaded from environment variables, with safe
defaults where appropriate.

Environment variables:
- FRONTEND_ORIGIN: Allowed CORS origin for the frontend (default: http://localhost:3000)
- ENABLE_SUPABASE: Whether Supabase integration is enabled ("true"/"false", default: false)
- SUPABASE_URL: Supabase project URL (optional)
- SUPABASE_SERVICE_ROLE_KEY: Supabase service role key (optional, sensitive)
- SUPABASE_ANON_KEY: Supabase anonymous key (optional, used by frontend or limited server use)
- SUPABASE_JWT_SECRET: Supabase JWT secret (optional, sensitive)
"""
from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from a .env file if present.
# This is safe for local dev; in production, envs should be provided by the orchestrator.
load_dotenv()


def _get_bool_env(name: str, default: bool = False) -> bool:
    """
    Parse a boolean-like environment variable safely.

    Accepts true/false variants (case-insensitive).
    """
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "y", "on")


# PUBLIC_INTERFACE
class Settings:
    """Application settings loaded from environment variables."""

    # CORS / Frontend origin
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

    # Optional Supabase configuration
    ENABLE_SUPABASE: bool = _get_bool_env("ENABLE_SUPABASE", default=False)
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL") or None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or None
    SUPABASE_ANON_KEY: Optional[str] = os.getenv("SUPABASE_ANON_KEY") or None
    SUPABASE_JWT_SECRET: Optional[str] = os.getenv("SUPABASE_JWT_SECRET") or None

    # PUBLIC_INTERFACE
    @staticmethod
    def supabase_is_configured() -> bool:
        """
        Determine if Supabase can be considered configured for optional usage.

        Returns True only if:
        - ENABLE_SUPABASE is True
        - SUPABASE_URL is present
        - And at least one of SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY is present
        """
        if not Settings.ENABLE_SUPABASE:
            return False
        if not Settings.SUPABASE_URL:
            return False
        if not (Settings.SUPABASE_SERVICE_ROLE_KEY or Settings.SUPABASE_ANON_KEY):
            return False
        return True


# Singleton-like settings instance for convenient import across the app
settings = Settings()
