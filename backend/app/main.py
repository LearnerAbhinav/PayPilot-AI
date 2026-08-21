import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.routers import auth, transactions, analytics, forecast, anomalies, ai, actions, audit, investigations, monitoring

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting PayPilot AI backend...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down PayPilot AI backend...")


app = FastAPI(
    title="PayPilot AI",
    description="Autonomous AI financial operations agent for online merchants",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(analytics.router)
app.include_router(forecast.router)
app.include_router(anomalies.router)
app.include_router(ai.router)
app.include_router(actions.router)
app.include_router(audit.router)
app.include_router(investigations.router)
app.include_router(monitoring.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Sanitize sensitive headers before logging
    safe_headers = {
        k: ("[REDACTED]" if k.lower() in ("authorization", "cookie", "proxy-authorization", "x-api-key") else v)
        for k, v in request.headers.items()
    }
    logger.info(f"Incoming Request: {request.method} {request.url.path} | Headers: {safe_headers}")
    return await call_next(request)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"},
    )


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "paypilot-ai"}
