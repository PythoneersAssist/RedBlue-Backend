from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import MetaData
from database.database import get_db, ENGINE
from database.models import Match, Base

from utils import generator
from api import endpoints


app = FastAPI()
metadata = MetaData()
metadata.reflect(ENGINE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(endpoints.router, prefix="/api")

Base.metadata.create_all(bind=ENGINE)

@app.get("/")
def main() -> str:
    return "OK"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True, port=8080)