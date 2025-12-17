import os
import io
import json
import base64
import asyncio
from PIL import Image
from typing import List, Dict, Any
from psycopg import AsyncConnection
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, UploadFile, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates

# Database connection - supports both Heroku DATABASE_URL and individual env vars
database_url = os.getenv("DATABASE_URL")
if not database_url:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "thanksgiving_db")
    user = os.getenv("POSTGRES_USER", "thanksgiving_user")
    password = os.getenv("POSTGRES_PASSWORD", "password")
    database_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

app = FastAPI()
templates = Jinja2Templates(directory="templates")

class ConnectionManager:
    """Manages WebSocket connections for real-time broadcasting"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast new message to all connected clients"""
        if self.active_connections:
            message_json = json.dumps(message)
            for connection in self.active_connections:
                try:
                    await connection.send_text(message_json)
                except: # Remove disconnected clients
                    self.disconnect(connection)

manager = ConnectionManager()

@app.get("/")
async def upload_page(request: Request):
    """Serve the upload page from templates/upload.html"""
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
async def upload(
    message: str = Form(...), # required
    user_name: str = Form(""),
    group_name: str = Form(""),
    event: str = Form(""),
    image: UploadFile | None = None
):
    """Endpoint to upload form data to database and broadcast to display clients"""
    status = "failed"
    warning_msg = None
    error_msg = None
    # Validate the uploaded image (if any)
    img = None
    img_binary = None
    if image:
        img_binary = await image.read()
        try:
            img = Image.open(io.BytesIO(img_binary))
        except:
            warning_msg = "Uploaded file is not a valid image"
    # Insert into the database
    try:
        con = await AsyncConnection.connect(database_url)
        async with con.cursor() as cur:
            # Always insert message
            await cur.execute("""
                INSERT INTO messages
                (message, has_image, user_name, group_name, event)
                VALUES (%s, %s, %s, %s, %s);
            """, (message, image is not None, user_name, group_name, event))
            # Insert image if provided
            if img:
                await cur.execute("""
                    INSERT INTO images
                    (message, image, user_name, group_name, event)
                    VALUES (%s, %s, %s, %s, %s);
                """, (message, img_binary, user_name, group_name, event))
            await con.commit()
    except Exception as e:
        error_msg = f"Database error: {e}"
        return {"status": status, "error": error_msg, "warning": warning_msg}
    finally:
        await con.close()
    # Broadcast new message to all display clients in real-time
    try:
        upload_time = datetime.now(timezone(timedelta(hours=8))).isoformat()
        data = {
            "message": message,
            "user_name": user_name or "匿名",
            "group_name": group_name or "",
            "event": event or "",
            "upload_time": upload_time,
            "has_image": image is not None
        }
        # If there's an image, include it in the broadcast
        if img:
            data["image"] = base64.b64encode(img_binary).decode('utf-8')
        # Broadcast to all connected WebSocket clients
        await manager.broadcast_message({
            "type": "new_message",
            "data": data
        })
    except Exception as e:
        warning_msg = f"Failed to broadcast message: {e}"
    status = "success"
    return {"status": status, "error": error_msg, "warning": warning_msg}

@app.get("/display")
async def display_page(request: Request):
    """Display page with real-time comment feed"""
    return templates.TemplateResponse("display.html", {"request": request})

@app.get("/messages")
async def get_messages(limit: int = 20):
    """Get recent messages for initial load"""
    async with await AsyncConnection.connect(database_url) as con:
        async with con.cursor() as cur:
            await cur.execute("""
                SELECT
                message, has_image, user_name, group_name, event, upload_time
                FROM messages
                ORDER BY upload_time DESC
                LIMIT %s
            """, (limit,))
            messages = await cur.fetchall()
            return [{
                "message": msg[0],
                "has_image": msg[1],
                "user_name": msg[2] or "匿名",
                "group_name": msg[3] or "",
                "event": msg[4] or "",
                "upload_time": msg[5].isoformat()
            } for msg in messages]

@app.get("/images")
async def get_images(limit: int = 10):
    """Get recent images for display"""
    async with await AsyncConnection.connect(database_url) as con:
        async with con.cursor() as cur:
            await cur.execute("""
                SELECT
                message, image, user_name, group_name, event, upload_time
                FROM images
                ORDER BY RANDOM()
                LIMIT %s
            """, (limit,))
            images = await cur.fetchall()
            return [{
                "message": img[0],
                "image": base64.b64encode(img[1]).decode('utf-8'),
                "user_name": img[2] or "匿名",
                "group_name": img[3] or "",
                "event": img[4] or "",
                "upload_time": img[5].isoformat()
            } for img in images]

@app.get("/admin/health-check")
async def health_check():
    """Health check endpoint for monitoring and testing"""
    try:
        # Test database by calling actual endpoints
        await get_messages(limit=1)
        await get_images(limit=1)
        health = "healthy"
        error_msg = None
    except Exception as e:
        health = "unhealthy"
        error_msg = str(e)
    return {"status": health, "error": error_msg}

@app.post("/admin/reset-database")
async def reset_database():
    """Reset database for testing purposes - USE WITH CAUTION"""
    async with await AsyncConnection.connect(database_url) as con:
        async with con.cursor() as cur:
            await cur.execute(
                "TRUNCATE TABLE images, messages RESTART IDENTITY CASCADE")
            await con.commit()
    return {"status": "success", "message": "Database reset successfully"}

@app.post("/admin/stress-test")
async def run_stress_test(users: int = 10, duration: str = "30s"):
    """Trigger Locust stress test via API endpoint (non-blocking)"""
    # Run Locust stress test asynchronously (non-blocking)
    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--host", "http://localhost:8000",
        "--headless",
        "--users", str(users),
        "--run-time", duration
    ]
    # start async process
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    # Wait for process to complete and get results
    stdout, _ = await process.communicate()
    # Check if test completed successfully
    status = "success" if process.returncode == 0 else "fail"
    return {"status": status, "stdout": stdout.decode('utf-8')}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True: # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
