"""
k360_token_python

This package provides utilities for managing JWT access tokens for secure
authentication with the Kount API.

Exports:
- token_manager: Singleton instance for accessing and storing tokens.
- fetch_or_refresh_token: Coroutine to retrieve a new token from the auth server.
- start_token_refresh_timer: Coroutine that runs in the background to refresh tokens proactively.
"""
from .jwt_utils import token_manager, fetch_or_refresh_token, start_token_refresh_timer
from .lifespan import token_lifespan