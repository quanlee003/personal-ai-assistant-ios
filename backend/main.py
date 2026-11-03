from fastapi import FastAPI

app = FastAPI(title="Personal AI Assistant API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}