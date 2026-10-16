"""Shared test helpers.

Tests never touch a real database or network: the Postgres pool is replaced by FakePool,
and the upload service's call to the display service is intercepted.
"""

import io
import os
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)  # the apps load templates/ relative to the working directory


class FakeCursor:
    def __init__(self, pool):
        self.pool = pool
        self._result = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, sql, params=None):
        if self.pool.fail:
            raise self.pool.fail
        self.pool.executed.append((" ".join(sql.split()), params))
        if sql.strip().startswith("INSERT INTO messages"):
            self._result = [(len(self.pool.executed), self.pool.now)]
        else:
            self._result = list(self.pool.rows)

    async def fetchone(self):
        return self._result[0]

    async def fetchall(self):
        return self._result


class FakeConnection:
    def __init__(self, pool):
        self.pool = pool

    def cursor(self):
        return FakeCursor(self.pool)


class FakePool:
    """Stands in for psycopg_pool.AsyncConnectionPool.

    executed: list of (sql, params) run so far. rows: what SELECTs return.
    fail: an exception to raise on execute, to simulate a database error.
    """

    def __init__(self):
        self.executed = []
        self.rows = []
        self.fail = None
        self.now = datetime(2026, 10, 16, 2, 30, tzinfo=UTC)

    @asynccontextmanager
    async def connection(self):
        yield FakeConnection(self)


@pytest.fixture
def fake_pool():
    return FakePool()


def make_image_bytes(fmt="JPEG", size=(100, 50), mode="RGB", exif_orientation=None):
    img = Image.new(mode, size, "red" if mode == "RGB" else None)
    out = io.BytesIO()
    kwargs = {}
    if exif_orientation:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation  # Orientation tag
        kwargs["exif"] = exif
    img.save(out, fmt, **kwargs)
    return out.getvalue()
