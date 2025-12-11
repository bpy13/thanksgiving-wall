import os
import json
import base64
from typing import List, Dict, Any
from psycopg import AsyncConnection
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates

db_params = {
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT"),
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD")
}

app = FastAPI()
templates = Jinja2Templates(directory="templates")

class ConnectionManager:
    """Manages WebSocket connections for real-time broadcasting"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        N_client = len(self.active_connections)
        print(f"Client connected. Total connections: {N_client}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            N_client = len(self.active_connections)
            print(f"Client disconnected. Total connections: {N_client}")
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast new message from upload service to all clients"""
        if self.active_connections:
            message_json = json.dumps(message)
            for connection in self.active_connections:
                try:
                    await connection.send_text(message_json)
                except: # Remove disconnected clients
                    self.disconnect(connection)

manager = ConnectionManager()

@app.get("/")
async def index(request: Request):
    """Display page with real-time comment feed"""
    return templates.TemplateResponse("display.html", {"request": request})

@app.get("/messages")
async def get_messages(limit: int = 20):
    """Get recent messages for initial load"""
    async with await AsyncConnection.connect(**db_params) as con:
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
async def get_images(limit: int = 20):
    """Get recent images for display"""
    async with await AsyncConnection.connect(**db_params) as con:
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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True: # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/notify")
async def notify(data: dict):
    """Internal endpoint called by upload service to broadcast new message"""
    await manager.broadcast_message({
        "type": "new_message", # for display.html
        "data": data
    })
    return {"status": "broadcasted"}
