from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import auth, dashboard, resources, optimization, reports, notifications
from app.services.optimizer_service import get_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    get_model()  # trains XGBoost on startup
    yield


app = FastAPI(
    title="IntelliOptiCloud API",
    description="AI-driven AWS Cost Optimization for Pakistani Startups & SMEs",
    version="1.7",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth, dashboard, resources, optimization, reports, notifications):
    app.include_router(router.router, prefix="/api")


@app.get("/")
def root():
    return {"app": "IntelliOptiCloud", "version": "1.7", "status": "running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}