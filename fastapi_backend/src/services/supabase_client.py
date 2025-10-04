"""
Supabase client stub for the backend.

This module conditionally exposes a "client" placeholder if Supabase is enabled
and minimally configured. No external SDKs are imported here. In future,
replace the stub with an actual Supabase client initialization.

Usage:
    from src.services.supabase_client import get_supabase

    client = get_supabase()
    if client is not None:
        # Use client (future integration)
        pass
    else:
        # Supabase is disabled or not configured; proceed without it.
        pass
"""
from __future__ import annotations

from typing import Any, Optional

from src.config import settings


# PUBLIC_INTERFACE
def get_supabase() -> Optional[Any]:
    """
    Returns a Supabase client placeholder if enabled and configured; otherwise None.

    Conditions:
    - ENABLE_SUPABASE must be true
    - SUPABASE_URL must be set
    - At least one of SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY must be set

    Implementation notes:
    - This is a stub; it does not create a real client or perform network calls.
    - Future integration can import an actual SDK and initialize it here.
    """
    if not settings.supabase_is_configured():
        return None

    # TODO: Replace with real Supabase SDK initialization when integrating.
    # Example placeholder to indicate presence without adding dependencies.
    client_stub = {
        "type": "supabase-client-stub",
        "url": settings.SUPABASE_URL,
        "auth": "service_role"
        if settings.SUPABASE_SERVICE_ROLE_KEY
        else "anon",
        # Do not include secrets in logs or public returns.
    }
    return client_stub
