"""Upload service: the form members use to post a message (and optional photo).

Saves the message to Postgres, then asks the display service to show it live.
"""

import base64
import io
import logging
import os
import uuid

import httpx
from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("upload")

# Settings (see .env.example)
DISPLAY_SERVICE_URL = os.getenv("DISPLAY_SERVICE_URL", "http://localhost:5001")
NOTIFY_TOKEN = os.getenv("NOTIFY_TOKEN", "")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "15"))
MAX_IMAGE_SIDE = 1920  # longest side after resizing, in pixels
JPEG_QUALITY = 85
NOTIFY_TIMEOUT_SECONDS = 5.0

# Messages shown to members (Traditional Chinese)
MSG_EMPTY = "請輸入感恩訊息。"
MSG_TOO_LARGE = "照片檔案太大（上限 {mb} MB），請選擇較小的照片再試一次。"
MSG_NOT_IMAGE = "上傳的檔案不是有效的圖片，訊息已分享，但沒有附上照片。"
MSG_NOT_SHOWN = "訊息已儲存，但未能即時顯示在螢幕上；螢幕重新載入後便會出現。"
MSG_SERVER_ERROR = "系統暫時出現問題，請稍後再試。（參考編號：{ref}）"

app = FastAPI(lifespan=db.lifespan)
templates = Jinja2Templates(directory="templates")


class InvalidImage(Exception):
    """The uploaded file could not be read as an image."""


def prepare_image(raw: bytes) -> bytes:
    """Validate a photo and turn it into a display-sized JPEG.

    Applies the EXIF orientation (phones store photos sideways and record the rotation),
    shrinks it to fit within MAX_IMAGE_SIDE, and re-encodes it as JPEG, which is what the
    display page expects. Raises InvalidImage if the file isn't a readable image.
    """
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            probe.verify()  # cheap structural check; the image must be reopened afterwards
        with Image.open(io.BytesIO(raw)) as img:
            img = ImageOps.exif_transpose(img)  # also fully decodes the image
            img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                # JPEG has no transparency: put the photo on a white background
                rgba = img.convert("RGBA")
                img = Image.new("RGB", rgba.size, "white")
                img.paste(rgba, mask=rgba.getchannel("A"))
            elif img.mode != "RGB":
                img = img.convert("RGB")
            out = io.BytesIO()
            img.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
            return out.getvalue()
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
        Image.DecompressionBombError,
    ) as e:
        raise InvalidImage(str(e)) from e


def result(
    status: str, error: str | None = None, warning: str | None = None, code: int = 200
) -> JSONResponse:
    """The JSON shape the upload page reads: {status, error, warning}."""
    return JSONResponse({"status": status, "error": error, "warning": warning}, status_code=code)


async def notify_display(data: dict) -> None:
    """Ask the display service to push the new message to every open display page."""
    async with httpx.AsyncClient(timeout=NOTIFY_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{DISPLAY_SERVICE_URL}/notify", json=data, headers={"X-Notify-Token": NOTIFY_TOKEN}
        )
        response.raise_for_status()


@app.get("/")
async def index(request: Request):
    """Serve the upload page from templates/upload.html"""
    return templates.TemplateResponse(request, "upload.html", {"max_upload_mb": MAX_UPLOAD_MB})


@app.post("/upload")
async def upload(
    request: Request,
    message: str = Form(...),  # required
    user_name: str = Form(""),
    group_name: str = Form(""),
    event: str = Form(""),
    image: UploadFile | None = None,
):
    """Save the message (and photo, if valid) and notify the display service."""
    if not message.strip():
        return result("failed", error=MSG_EMPTY, code=400)

    warning = None
    jpeg = None
    if image is not None:
        max_bytes = MAX_UPLOAD_MB * 1024 * 1024
        raw = await image.read(max_bytes + 1)
        if len(raw) > max_bytes:
            return result("failed", error=MSG_TOO_LARGE.format(mb=MAX_UPLOAD_MB), code=413)
        if raw:  # an empty file part means "no photo"
            try:
                # Decoding and resizing is CPU work; run it off the event loop
                jpeg = await run_in_threadpool(prepare_image, raw)
            except InvalidImage as e:
                logger.info("Rejected invalid image %r: %s", image.filename, e)
                warning = MSG_NOT_IMAGE

    # Save the message, and the photo linked to it, in one transaction
    try:
        async with request.app.state.pool.connection() as con, con.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO messages (message, has_image, user_name, group_name, event)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, upload_time
                """,
                (message, jpeg is not None, user_name, group_name, event),
            )
            message_id, upload_time = await cur.fetchone()
            if jpeg is not None:
                await cur.execute(
                    "INSERT INTO images (message_id, image) VALUES (%s, %s)",
                    (message_id, jpeg),
                )
    except Exception:
        ref = uuid.uuid4().hex[:8]
        logger.exception("Database error saving upload (ref %s)", ref)
        return result("failed", error=MSG_SERVER_ERROR.format(ref=ref), code=500)

    # The message is saved. From here on, problems are warnings, not failures.
    data = {
        "message": message,
        "user_name": user_name or "匿名",
        "group_name": group_name or "",
        "event": event or "",
        "upload_time": upload_time.isoformat(),
        "has_image": jpeg is not None,
    }
    if jpeg is not None:
        data["image"] = base64.b64encode(jpeg).decode("ascii")
    try:
        await notify_display(data)
    except httpx.HTTPError as e:
        logger.warning(
            "Saved message %s but could not notify the display service: %r", message_id, e
        )
        warning = f"{warning} {MSG_NOT_SHOWN}" if warning else MSG_NOT_SHOWN

    return result("success", warning=warning)
