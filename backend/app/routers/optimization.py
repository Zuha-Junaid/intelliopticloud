from fastapi import APIRouter
from app.services.optimizer_service import predict_memory, recommend_spot, get_accuracy, _train
from app.services.cloudwatch_service import get_functions

router = APIRouter(prefix="/optimization", tags=["Optimization"])

@router.get("/model-info")
def model_info():
    return {
        "algorithm": "XGBoost Regressor",
        "trainedOn": "Synthetic cloud usage data (5,000 samples)",
        "accuracy": get_accuracy(),
        "version": "v2.3.1",
        "features": ["Memory MB", "Invocations", "Avg Duration", "Cold Start Ratio", "Hour of Day", "Memory Utilization %"],
    }

@router.get("/pipeline")
def pipeline():
    return {"stages": [
        {"id": 1, "stage": "Data Collection", "desc": "Pulling Lambda metrics from CloudWatch APIs", "status": "complete"},
        {"id": 2, "stage": "Feature Engineering", "desc": "Processing usage patterns for model input", "status": "complete"},
        {"id": 3, "stage": "XGBoost Prediction", "desc": "Predicting optimal memory & instance config", "status": "complete"},
        {"id": 4, "stage": "Decision Validation", "desc": "Simulating cost impact before applying", "status": "complete"},
        {"id": 5, "stage": "Zero-Downtime Deployment", "desc": "Applying AWS Lambda configuration update", "status": "active"},
    ]}

@router.get("/recommendations")
def recommendations():
    fns = get_functions()
    result = []
    for fn in fns:
        result.append({
            "function": fn["name"],
            "memory": predict_memory(fn["memory"], fn["invocations"], fn["avgDuration"]),
            "spot": recommend_spot(fn["invocations"], fn["avgDuration"]),
        })
    return {"recommendations": result}

@router.post("/retrain")
def retrain():
    _train()
    return {"message": "Model retrained", "accuracy": get_accuracy()}