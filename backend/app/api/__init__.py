"""API routers."""
from app.api.complaints import router as complaints_router
from app.api.ai import router as ai_router

__all__ = ["ai_router", "complaints_router"]
