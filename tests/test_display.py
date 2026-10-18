import asyncio
import json
from datetime import UTC, datetime

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

import display

TOKEN = "test-token"


@pytest.fixture
def client(fake_pool, monkeypatch):
    monkeypatch.setattr(display, "NOTIFY_TOKEN", TOKEN)
    monkeypatch.setattr(display, "manager", display.ConnectionManager())
    display.app.state.pool = fake_pool
    return TestClient(display.app)


class FakeSocket:
    def __init__(self, error=None):
        self.sent = []
        self.error = error

    async def send_text(self, text):
        if self.error:
            raise self.error
        self.sent.append(text)


@pytest.mark.parametrize("error", [RuntimeError("closed"), WebSocketDisconnect(1006), OSError()])
def test_broadcast_skips_nobody_after_dead_connection(error):
    manager = display.ConnectionManager()
    alive_1, dead, alive_2, alive_3 = FakeSocket(), FakeSocket(error), FakeSocket(), FakeSocket()
    manager.active_connections = [alive_1, dead, alive_2, alive_3]

    asyncio.run(manager.broadcast_message({"type": "new_message", "data": {"message": "hi"}}))

    for sock in (alive_1, alive_2, alive_3):
        assert len(sock.sent) == 1
    assert manager.active_connections == [alive_1, alive_2, alive_3]


def test_two_dead_connections_in_a_row_are_both_removed():
    manager = display.ConnectionManager()
    dead_1, dead_2, alive = FakeSocket(RuntimeError()), FakeSocket(RuntimeError()), FakeSocket()
    manager.active_connections = [dead_1, dead_2, alive]
    asyncio.run(manager.broadcast_message({"x": 1}))
    assert manager.active_connections == [alive]
    assert len(alive.sent) == 1


@pytest.mark.parametrize("headers", [{}, {"X-Notify-Token": "wrong"}, {"X-Notify-Token": ""}])
def test_notify_rejects_missing_or_wrong_token(client, headers):
    r = client.post("/notify", json={"message": "spam"}, headers=headers)
    assert r.status_code == 401


def test_notify_rejects_everything_when_no_token_configured(client, monkeypatch):
    monkeypatch.setattr(display, "NOTIFY_TOKEN", "")
    r = client.post("/notify", json={"message": "x"}, headers={"X-Notify-Token": ""})
    assert r.status_code == 401


def test_notify_with_token_reaches_websocket_client(client):
    with client.websocket_connect("/ws") as ws:
        r = client.post("/notify", json={"message": "感謝主"}, headers={"X-Notify-Token": TOKEN})
        assert r.json() == {"status": "broadcasted"}
        got = json.loads(ws.receive_text())
    assert got == {"type": "new_message", "data": {"message": "感謝主"}}


def test_messages_shape_and_limit_clamp(client, fake_pool):
    t = datetime(2026, 10, 16, 2, 30, tzinfo=UTC)
    fake_pool.rows = [("感謝", True, None, None, None, t)]
    body = client.get("/messages?limit=100000").json()
    assert body == [
        {
            "message": "感謝",
            "has_image": True,
            "user_name": "匿名",
            "group_name": "",
            "event": "",
            "upload_time": t.isoformat(),
        }
    ]
    assert fake_pool.executed[-1][1] == (display.MAX_MESSAGES_LIMIT,)
    client.get("/messages?limit=-5")
    assert fake_pool.executed[-1][1] == (1,)
    client.get("/messages")
    assert fake_pool.executed[-1][1] == (20,)


def test_images_lists_photo_urls_not_photo_bytes(client, fake_pool):
    t = datetime(2026, 10, 16, 2, 30, tzinfo=UTC)
    fake_pool.rows = [(7, "感謝", "Amy", "D21", "感恩會", t)]
    body = client.get("/images?limit=999").json()
    assert body == [
        {
            "url": "/images/7",
            "message": "感謝",
            "user_name": "Amy",
            "group_name": "D21",
            "event": "感恩會",
            "upload_time": t.isoformat(),
        }
    ]
    sql, params = fake_pool.executed[-1]
    assert "JOIN messages m ON m.id = i.message_id" in sql
    assert "i.image" not in sql  # the list must stay small: no photo bytes in it
    assert params == (display.MAX_IMAGES_LIMIT,)


@pytest.mark.parametrize(
    "data, media_type",
    [
        (b"\xff\xd8\xff\xe0jpeg", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\nold-png", "image/png"),  # photos stored before resizing existed
    ],
)
def test_single_image_bytes_type_and_cache_header(client, fake_pool, data, media_type):
    fake_pool.rows = [(data,)]
    r = client.get("/images/7")
    assert r.status_code == 200
    assert r.content == data
    assert r.headers["content-type"] == media_type
    assert "immutable" in r.headers["cache-control"]
    assert fake_pool.executed[-1][1] == (7,)


def test_single_image_missing_is_404(client, fake_pool):
    fake_pool.rows = []
    assert client.get("/images/999").status_code == 404
    assert client.get("/images/not-a-number").status_code == 422


def test_display_page_has_no_english_status_text(client):
    page = client.get("/").text
    assert "Connection error" not in page and "Just now" not in page
