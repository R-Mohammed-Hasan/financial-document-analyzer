"""
FastAPI application entrypoint for the Financial Document Analyzer backend.

This module initializes the FastAPI application with all necessary configurations,
middleware, routers, and dependencies.
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from core.config import settings
from core.rate_limiter import RateLimitMiddleware
from api.v1.auth import router as auth_router
from api.v1.users import router as users_router
from api.v1.files import router as files_router
from api.v1.analysis import router as analysis_router
from db.session import get_db

# Create FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(files_router, prefix=settings.API_V1_STR)
app.include_router(analysis_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "message": "Financial Document Analyzer API",
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health")
def health_check(db=Depends(get_db)):
    """Health check endpoint with database connectivity test."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {"status": "healthy", "database": db_status, "version": settings.VERSION}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
