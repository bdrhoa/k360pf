"""Test configuration for the account-protection example."""

import os
import sys
from pathlib import Path


os.environ.setdefault("KOUNT_API_KEY", "test-api-key")

ACCOUNT_PROTECTION_ROOT = Path(__file__).resolve().parents[1]
JWT_AUTH_SRC = ACCOUNT_PROTECTION_ROOT.parent / "jwt_auth" / "src"

sys.path.insert(0, str(ACCOUNT_PROTECTION_ROOT))
sys.path.insert(0, str(JWT_AUTH_SRC))
