#!/usr/bin/env python3
"""
Utility to regenerate the OpenAPI schema for the FastAPI app.

This script imports the FastAPI app from src.api.main and writes the output of
app.openapi() to interfaces/openapi.json. The output directory is created if it
does not exist.

Usage:
    python scripts/generate_openAPI.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root (fastapi_backend) is in sys.path for "src" imports
# Resolve this script's directory: <base>/fastapi_backend/scripts
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent  # <base>/fastapi_backend
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    # Import the FastAPI app
    from src.api.main import app  # noqa: E402
except Exception as e:
    print(f"ERROR: Failed to import FastAPI app from src.api.main: {e}", file=sys.stderr)
    sys.exit(1)

def main() -> int:
    """Generate and write OpenAPI schema to interfaces/openapi.json."""
    try:
        schema = app.openapi()
    except Exception as e:
        print(f"ERROR: Failed to generate OpenAPI schema via app.openapi(): {e}", file=sys.stderr)
        return 2

    interfaces_dir = BACKEND_ROOT / "interfaces"
    interfaces_dir.mkdir(parents=True, exist_ok=True)
    output_path = interfaces_dir / "openapi.json"

    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"ERROR: Failed to write OpenAPI schema to {output_path}: {e}", file=sys.stderr)
        return 3

    print(f"OpenAPI schema written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
