import base64
import io
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import upload
from tests.conftest import make_image_bytes


@pytest.fixture
def notify_calls(monkeypatch):
    """Intercept the call to the display service; tests can set .fail to make it fail."""

    class Calls(list):
        fail = None  # exception to raise instead of answering
        status = 200  # HTTP status the fake display service answers with

    calls = Calls()

    def handler(request: httpx.Request):
        if calls.fail:
            raise calls.fail
        calls.append(request)
        return httpx.Response(calls.status, json={"status": "broadcasted"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        upload.httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    monkeypatch.setattr(upload, "NOTIFY_TOKEN", "test-token")
    return calls


@pytest.fixture
def client(fake_pool, notify_calls):
    # Not used as a context manager, so the real pool (lifespan) never opens
    upload.app.state.pool = fake_pool
    return TestClient(upload.app)


FORM = {"message": "感謝主", "user_name": "Amy", "group_name": "D21", "event": "感恩會"}


def inserts(pool, table):
    return [p for sql, p in pool.executed if sql.startswith(f"INSERT INTO {table}")]


def broadcast(notify_calls):
    return json.loads(notify_calls[0].content)


def test_upload_page_is_chinese(client):
    page = client.get("/").text
    assert "分享訊息" in page
    assert "Share Message" not in page and "Click to choose" not in page


def test_message_without_image(client, fake_pool, notify_calls):
    r = client.post("/upload", data=FORM)
    assert r.status_code == 200
    assert r.json() == {"status": "success", "error": None, "warning": None}
    assert inserts(fake_pool, "messages") == [("感謝主", False, "Amy", "D21", "感恩會")]
    assert inserts(fake_pool, "images") == []
    sent = broadcast(notify_calls)
    assert sent["has_image"] is False and "image" not in sent
    assert sent["upload_time"] == fake_pool.now.isoformat()  # time comes from the database
    assert notify_calls[0].headers["X-Notify-Token"] == "test-token"


def test_blank_message_rejected(client, fake_pool):
    r = client.post("/upload", data={**FORM, "message": "   "})
    assert r.status_code == 400
    assert r.json()["status"] == "failed"
    assert fake_pool.executed == []


def test_message_with_valid_image_is_resized_jpeg(client, fake_pool, notify_calls):
    png = make_image_bytes("PNG", size=(4000, 3000), mode="RGBA")
    r = client.post("/upload", data=FORM, files={"image": ("photo.png", png, "image/png")})
    assert r.json() == {"status": "success", "error": None, "warning": None}
    assert inserts(fake_pool, "messages")[0][1] is True  # has_image
    ((message_id, stored),) = inserts(fake_pool, "images")
    img = Image.open(io.BytesIO(stored))
    assert img.format == "JPEG"
    assert img.size == (1920, 1440)  # fits within 1920px, aspect kept
    sent = broadcast(notify_calls)
    assert sent["has_image"] is True
    assert base64.b64decode(sent["image"]) == stored


def test_exif_orientation_applied(client, fake_pool):
    # Orientation 6 = the camera was turned; the stored photo should come out upright
    jpg = make_image_bytes("JPEG", size=(200, 100), exif_orientation=6)
    client.post("/upload", data=FORM, files={"image": ("p.jpg", jpg, "image/jpeg")})
    ((_, stored),) = inserts(fake_pool, "images")
    assert Image.open(io.BytesIO(stored)).size == (100, 200)


def test_invalid_image_saves_message_without_photo(client, fake_pool, notify_calls):
    r = client.post(
        "/upload", data=FORM, files={"image": ("notes.txt", b"not an image at all", "text/plain")}
    )
    body = r.json()
    assert body["status"] == "success"
    assert body["warning"] == upload.MSG_NOT_IMAGE
    assert inserts(fake_pool, "messages")[0][1] is False  # has_image false
    assert inserts(fake_pool, "images") == []
    assert broadcast(notify_calls)["has_image"] is False


def test_huge_non_jpeg_is_not_decoded(client, fake_pool, monkeypatch):
    # A PNG can't be draft-scaled, so one over the pixel cap is refused rather than decoded
    monkeypatch.setattr(upload, "MAX_DECODE_PIXELS", 1000)
    png = make_image_bytes("PNG", size=(100, 100))
    body = client.post("/upload", data=FORM, files={"image": ("p.png", png, "image/png")}).json()
    assert body["warning"] == upload.MSG_NOT_IMAGE
    assert inserts(fake_pool, "images") == []


def test_large_jpeg_is_draft_scaled_and_accepted(client, fake_pool, monkeypatch):
    # 8000x6000 = 48 MP, over the cap; draft scaling decodes it at half size (12 MP), under it
    monkeypatch.setattr(upload, "MAX_DECODE_PIXELS", 13_000_000)
    jpg = make_image_bytes("JPEG", size=(8000, 6000))
    client.post("/upload", data=FORM, files={"image": ("p.jpg", jpg, "image/jpeg")})
    ((_, stored),) = inserts(fake_pool, "images")
    assert max(Image.open(io.BytesIO(stored)).size) <= 1920


def test_truncated_image_is_invalid(client, fake_pool):
    jpg = make_image_bytes("JPEG", size=(400, 400))
    client.post("/upload", data=FORM, files={"image": ("p.jpg", jpg[:200], "image/jpeg")})
    assert inserts(fake_pool, "images") == []


def test_oversize_image_rejected(client, fake_pool, notify_calls, monkeypatch):
    monkeypatch.setattr(upload, "MAX_UPLOAD_MB", 1)
    big = b"\xff\xd8" + b"0" * (1024 * 1024)
    r = client.post("/upload", data=FORM, files={"image": ("big.jpg", big, "image/jpeg")})
    assert r.status_code == 413
    body = r.json()
    assert body["status"] == "failed"
    assert "1 MB" in body["error"] and "太大" in body["error"]
    assert fake_pool.executed == []  # nothing saved
    assert notify_calls == []


def test_notify_failure_is_success_with_warning(client, fake_pool, notify_calls):
    notify_calls.fail = httpx.ConnectError("display service down")
    r = client.post("/upload", data=FORM)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["error"] is None
    assert body["warning"] == upload.MSG_NOT_SHOWN
    assert len(inserts(fake_pool, "messages")) == 1


def test_notify_rejected_token_is_warning(client, notify_calls):
    # The display service answering 401 (wrong token) must not look like a success
    notify_calls.status = 401
    body = client.post("/upload", data=FORM).json()
    assert body["status"] == "success"
    assert body["warning"] == upload.MSG_NOT_SHOWN


def test_database_error_returns_generic_message(client, fake_pool, notify_calls, caplog):
    fake_pool.fail = RuntimeError("password authentication failed for user admin")
    r = client.post("/upload", data=FORM)
    assert r.status_code == 500
    body = r.json()
    assert body["status"] == "failed"
    assert "password" not in body["error"]
    assert "參考編號" in body["error"]
    ref = body["error"].split("：")[-1].rstrip("）")
    assert ref in caplog.text  # the same reference is in the log, with the details
    assert "password authentication failed" in caplog.text
    assert notify_calls == []


def test_database_connect_failure_is_not_masked(client, fake_pool):
    # Bug 2: a failed connect used to raise NameError from the finally block
    fake_pool.fail = OSError("connection refused")
    r = client.post("/upload", data=FORM)
    assert r.status_code == 500
    assert r.json()["status"] == "failed"
