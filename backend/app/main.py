"""FastAPI application entrypoint."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai_router, complaints_router
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-powered Customer Complaint Management System for pharmaceutical "
        "manufacturing (API/FDF). LangGraph + Groq agent handles form "
        "auto-population and Copilot risk assessment. Interactive docs at /docs."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(complaints_router)
app.include_router(ai_router)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    from app.database import engine
    try:
        with engine.connect():
            db_ok = True
    except Exception as e:  # pragma: no cover
        db_ok = str(e)
    return {"status": "ok", "database": db_ok, "groq_configured": settings.groq_configured}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
