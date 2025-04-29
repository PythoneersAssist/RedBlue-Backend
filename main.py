"""
MAIN
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import MetaData
from database.database import ENGINE
from database.models import Base

from api import endpoints
from debug import debug_endpoints


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
app.include_router(debug_endpoints.router)

Base.metadata.create_all(bind=ENGINE)

@app.get("/")
def main() -> str:
    """Health check function"""
    return "OK"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True, port=8080)
