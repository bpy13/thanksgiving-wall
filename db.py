"""Shared Postgres connection pool for the upload and display services."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool


def connection_kwargs() -> dict:
    """Connection settings, read from the environment (see .env.example)."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "dbname": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the pool when the app starts and close it on shutdown.

    The pool opens without waiting, so the service starts even if Postgres is still booting;
    the pool keeps retrying in the background and requests wait for a free connection.
    """
    pool = AsyncConnectionPool(
        kwargs=connection_kwargs(),
        min_size=1,
        max_size=int(os.getenv("DB_POOL_MAX", "5")),
        # Test each connection before handing it out, so a Postgres restart doesn't make the
        # next request fail on a connection the server has already closed.
        check=AsyncConnectionPool.check_connection,
        open=False,
    )
    await pool.open(wait=False)
    app.state.pool = pool
    try:
        yield
    finally:
        await pool.close()
