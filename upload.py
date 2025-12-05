import os
import io
from PIL import Image
from psycopg import AsyncConnection
from fastapi import FastAPI, UploadFile, Form

db_params = {
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT"),
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD")
}

app = FastAPI()

@app.get("/")
def index():
    return {"upload:app": "Welcome to the Thanksgiving App!"}

@app.post("/upload")
async def upload(
    message: str = Form(...), # required
    user_name: str = Form(""),
    group_name: str = Form(""),
    event: str = Form(""),
    image: UploadFile | None = None
):
    """Upload to database: message (required) + image (optional)"""
    status = "failed"
    error_msg = None
    warning_msg = None
    # validate uploaded image (if any)
    img_binary = None
    if image:
        img_binary = await image.read()
        try: # by directly opening the image with Pillow
            img = Image.open(io.BytesIO(img_binary))
        except:
            warning_msg = "Uploaded file is not a valid image"
    # insert into database
    async with await AsyncConnection.connect(**db_params) as con:
        async with con.cursor() as cur:
            await cur.execute("""
                INSERT INTO messages
                (message, user_name, group_name, event)
                VALUES (%s, %s, %s, %s);
            """, (message, user_name, group_name, event))
            if image:
                await cur.execute("""
                    INSERT INTO images
                    (message, image, user_name, group_name, event)
                    VALUES (%s, %s, %s, %s, %s);
                """, (message, img_binary, user_name, group_name, event))
            await con.commit()
    status = "success"
    return {"status": status, "error": error_msg, "warning": warning_msg}
