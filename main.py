from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def main() -> str:
    return "OK"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True, port=8080)