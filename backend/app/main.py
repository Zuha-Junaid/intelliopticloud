from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import auth, dashboard, resources, optimization, reports, notifications
from app.security import get_current_user
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

# Only the local dev server and Vercel-hosted frontends may call the API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Login/register stay public; everything else requires a valid token.
app.include_router(auth.router, prefix="/api")
for router in (dashboard, resources, optimization, reports, notifications):
    app.include_router(router.router, prefix="/api", dependencies=[Depends(get_current_user)])


@app.get("/")
def root():
    return {"app": "IntelliOptiCloud", "version": "1.7", "status": "running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}