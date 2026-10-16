"""Display service: the live wall shown on the projector.

Serves the display page, recent messages and photos, and pushes new uploads to every open
display page over a WebSocket.
"""

import base64
import json
import logging
import os
import secrets
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates

import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("display")

# Settings (see .env.example)
NOTIFY_TOKEN = os.getenv("NOTIFY_TOKEN", "")
MAX_MESSAGES_LIMIT = 100
MAX_IMAGES_LIMIT = 30  # photos are a few hundred KB each, so keep this modest

app = FastAPI(lifespan=db.lifespan)
templates = Jinja2Templates(directory="templates")

if not NOTIFY_TOKEN:
    logger.warning(
        "NOTIFY_TOKEN is not set: /notify will reject every call, so new uploads "
        "will not appear live. Set it in .env."
    )


class ConnectionManager:
    """Manages WebSocket connections for real-time broadcasting"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_message(self, message: dict[str, Any]):
        """Send a message to every connected display page, dropping any that have gone."""
        message_json = json.dumps(message)
        # Iterate over a copy: disconnect() changes the list, and changing a list while
        # looping over it skips the item after each removed one.
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message_json)
            except (WebSocketDisconnect, RuntimeError, OSError) as e:
                # Closed or broken socket (RuntimeError: send after close)
                logger.info("Dropping disconnected display client: %r", e)
                self.disconnect(connection)


manager = ConnectionManager()


def clamp(value: int, upper: int) -> int:
    return max(1, min(value, upper))


@app.get("/")
async def index(request: Request):
    """Display page with real-time comment feed"""
    return templates.TemplateResponse(request, "display.html")


@app.get("/messages")
async def get_messages(request: Request, limit: int = 20):
    """Get recent messages for initial load"""
    async with request.app.state.pool.connection() as con, con.cursor() as cur:
        await cur.execute(
            """
            SELECT message, has_image, user_name, group_name, event, upload_time
            FROM messages
            ORDER BY upload_time DESC
            LIMIT %s
            """,
            (clamp(limit, MAX_MESSAGES_LIMIT),),
        )
        rows = await cur.fetchall()
    return [
        {
            "message": row[0],
            "has_image": row[1],
            "user_name": row[2] or "匿名",
            "group_name": row[3] or "",
            "event": row[4] or "",
            "upload_time": row[5].isoformat(),
        }
        for row in rows
    ]


@app.get("/images")
async def get_images(request: Request, limit: int = 10):
    """Get a random selection of photos, with their message details, for the slideshow"""
    async with request.app.state.pool.connection() as con, con.cursor() as cur:
        await cur.execute(
            """
            SELECT m.message, i.image, m.user_name, m.group_name, m.event, m.upload_time
            FROM images i
            JOIN messages m ON m.id = i.message_id
            ORDER BY RANDOM()
            LIMIT %s
            """,
            (clamp(limit, MAX_IMAGES_LIMIT),),
        )
        rows = await cur.fetchall()
    return [
        {
            "message": row[0],
            "image": base64.b64encode(row[1]).decode("ascii"),
            "user_name": row[2] or "匿名",
            "group_name": row[3] or "",
            "event": row[4] or "",
            "upload_time": row[5].isoformat(),
        }
        for row in rows
    ]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:  # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


@app.post("/notify")
async def notify(data: dict, x_notify_token: str = Header(default="")):
    """Internal endpoint called by the upload service to broadcast a new message.

    Requires the shared NOTIFY_TOKEN in the X-Notify-Token header, so people on the network
    can't post to the wall directly.
    """
    if not NOTIFY_TOKEN or not secrets.compare_digest(
        x_notify_token.encode(), NOTIFY_TOKEN.encode()
    ):
        raise HTTPException(status_code=401, detail="invalid notify token")
    await manager.broadcast_message({"type": "new_message", "data": data})  # for display.html
    return {"status": "broadcasted"}
