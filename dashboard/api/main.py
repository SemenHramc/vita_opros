from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, status, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.security import APIKeyHeader

from bot.config import settings
from bot.database import engine
from bot.logging_config import configure_logging, get_logger
from dashboard.api.routes import router

configure_logging(json_format=False)
logger = get_logger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    logger.info("verify_api_key_called", api_key_present=x_api_key is not None)
    if x_api_key is None or x_api_key != settings.dashboard_api_key:
        logger.warning("api_key_invalid", provided=x_api_key, expected=settings.dashboard_api_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("dashboard_starting", host=settings.dashboard_host, port=settings.dashboard_port)
    yield
    await engine.dispose()
    logger.info("dashboard_shutdown_complete")


app = FastAPI(title="Vita Opros Dashboard", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.dashboard_allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", dependencies=[Depends(verify_api_key)])


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.error("validation_error", errors=exc.errors(), body=body.decode())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.api_route("/health", methods=["GET", "HEAD"], tags=["health"])
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        logger.debug("health_check_passed")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "healthy", "database": "connected"},
        )
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)},
        )


frontend_dist = Path(__file__).parent.parent / "frontend" / "build"
frontend_static = frontend_dist / "static"
if frontend_dist.exists() and frontend_static.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_static)), name="static")
    logger.info("static_mounted", path=str(frontend_static))

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(str(frontend_dist / "index.html"))
    
    logger.info("spa_fallback_configured")