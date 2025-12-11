import os
import io
import httpx
import base64
from PIL import Image
from psycopg import AsyncConnection
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, UploadFile, Form, Request
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
display_service_url = os.getenv("DISPLAY_SERVICE_URL", "http://localhost:8001")

@app.get("/")
async def index(request: Request):
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
    """Endpoint to upload form data to database and notify display service"""
    status = "failed"
    warning_msg = None
    # validate the uploaded image (if any)
    img = None
    if image:
        img_binary = await image.read()
        try: # try-except by directly opening the image with Pillow
            img = Image.open(io.BytesIO(img_binary))
        except:
            warning_msg = "Uploaded file is not a valid image"
    # insert into the database
    try:
        con = await AsyncConnection.connect(**db_params)
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
    # Broadcast new message to the display service if upload is successful
    try:
        upload_time = datetime.now(timezone(timedelta(hours=8))).isoformat()
        data = {
            "message": message,
            "user_name": user_name or "Anonymous",
            "group_name": group_name or "",
            "event": event or "",
            "upload_time": upload_time,
            "has_image": image is not None
        }
        # If there's an image, include it in the broadcast
        if img:
            data["image"] = base64.b64encode(img_binary).decode('utf-8')
        # Notify the display service
        async with httpx.AsyncClient() as client:
            await client.post(f"{display_service_url}/notify", json=data)
    except Exception as e:
        warning_msg = f"Failed to broadcast message: {e}"
        return {"status": status, "error": error_msg, "warning": warning_msg}
    status = "success"
    return {"status": status, "error": None, "warning": warning_msg}
