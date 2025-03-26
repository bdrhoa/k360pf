"""
Token lifespan management for FastAPI apps.

This module provides an async context manager (`token_lifespan`) that handles
startup and shutdown logic for managing Kount API access tokens.

Usage:
    app = FastAPI(lifespan=token_lifespan)
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .jwt_utils import token_manager, fetch_or_refresh_token, start_token_refresh_timer


@asynccontextmanager
async def token_lifespan(app: FastAPI):
    """
    Manages the token lifecycle for FastAPI applications.

    On startup:
    - Fetches an access token from the authentication server
    - Starts a background task to refresh the token before expiration

    On shutdown:
    - Cancels the background token refresh task gracefully

    This can be used as the `lifespan` parameter when creating a FastAPI app:
        app = FastAPI(lifespan=token_lifespan)

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    print("🚀 Starting token lifespan manager")
    try:
        await fetch_or_refresh_token(token_manager)
        app.state.refresh_task = asyncio.create_task(start_token_refresh_timer(token_manager))
        print("✅ Token initialized successfully")
        yield
    finally:
        print("🛑 Shutting down token refresh task")
        app.state.refresh_task.cancel()
        try:
            await app.state.refresh_task
        except asyncio.CancelledError:
            pass  # Expected on shutdown