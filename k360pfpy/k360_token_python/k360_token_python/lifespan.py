"""
Token and public key lifespan management for FastAPI apps.

This module provides an async context manager (`token_lifespan`) that handles
startup and shutdown logic for managing Kount API access tokens and (optionally) public keys.

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
    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        """
        Manages the token and optionally public key lifecycle for FastAPI applications.

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

    return _lifespan