"""
Token and public key lifespan management for FastAPI apps.

This module provides a factory function (`token_lifespan`) that returns
an async context manager. It handles startup and shutdown logic for managing
Kount API access tokens and optionally webhook public key refresh logic.

Usage:
    app = FastAPI(lifespan=token_lifespan())                 # JWT only
    app = FastAPI(lifespan=token_lifespan(use_public_key=True))  # JWT + Public key
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .jwt_utils import token_manager, fetch_or_refresh_token, start_token_refresh_timer
from .pub_key_utils import fetch_public_key, start_public_key_refresh_timer


def token_lifespan(use_public_key: bool = False):
    """
    Creates a FastAPI lifespan context manager that manages the lifecycle of
    the Kount JWT token and optionally a webhook public key.

    Args:
        use_public_key (bool): If True, also fetches and refreshes the public key.

    Returns:
        Callable: An async context manager function for FastAPI's lifespan hook.
    """
    @asynccontextmanager
    async def lifespan_context(app: FastAPI):
        """
        The actual async context manager used by FastAPI to handle startup and shutdown.

        On startup:
            - Fetches and schedules refresh of JWT access token.
            - Optionally fetches and schedules refresh of public key.

        On shutdown:
            - Cancels background refresh tasks gracefully.

        Args:
            app (FastAPI): The FastAPI application instance.
        """
        print("🚀 Starting token lifespan manager")
        try:
            # JWT is always required
            await fetch_or_refresh_token(token_manager)
            app.state.refresh_task = asyncio.create_task(start_token_refresh_timer(token_manager))

            # Public key is optional
            if use_public_key:
                print("🔐 Public key support enabled")
                await fetch_public_key()
                app.state.public_key_task = asyncio.create_task(start_public_key_refresh_timer())

            print("✅ Lifespan initialization complete")
            yield

        finally:
            print("🛑 Shutting down refresh tasks")
            app.state.refresh_task.cancel()
            try:
                await app.state.refresh_task
            except asyncio.CancelledError:
                pass

            if use_public_key and hasattr(app.state, "public_key_task"):
                app.state.public_key_task.cancel()
                try:
                    await app.state.public_key_task
                except asyncio.CancelledError:
                    pass

    return lifespan_context