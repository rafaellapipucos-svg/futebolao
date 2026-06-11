"""Healthcheck do container: python -m app.healthcheck (exit 0 = saudável)."""
from __future__ import annotations

import os
import sys
import urllib.request


def main() -> int:
    port = os.environ.get("PORT", "8000")
    url = f"http://127.0.0.1:{port}/api/health"
    try:
        with urllib.request.urlopen(url, timeout=4) as resp:
            return 0 if resp.status == 200 else 1
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
