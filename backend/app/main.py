from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, dashboard, resources, optimization, reports, notifications
from app.services.optimizer_service import get_model

app = FastAPI(
    title="IntelliOptiCloud API",
    description="AI-driven AWS Cost Optimization for Pakistani Startups & SMEs",
    version="1.7",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(resources.router, prefix="/api")
app.include_router(optimization.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")

@app.on_event("startup")
def startup():
    print("Training XGBoost model...")
    get_model()
    print("Model ready. Server running.")

@app.get("/")
def root():
    return {"app": "IntelliOptiCloud", "version": "1.7", "status": "running", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "healthy"}