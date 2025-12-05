import os
from psycopg import AsyncConnection
from fastapi import FastAPI

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
    return {"display:app": "Welcome to the Thanksgiving App!"}

@app.post("/display")
async def display():
    """"""
    return {}
