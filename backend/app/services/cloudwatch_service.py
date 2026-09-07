import boto3
from datetime import datetime, timedelta
from app.config import settings

def get_lambda_client():
    return boto3.client(
        "lambda",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

def get_cloudwatch_client():
    return boto3.client(
        "cloudwatch",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

def get_metric(fn_name: str, metric: str) -> float:
    try:
        cw = get_cloudwatch_client()
        resp = cw.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName=metric,
            Dimensions=[{"Name": "FunctionName", "Value": fn_name}],
            StartTime=datetime.utcnow() - timedelta(days=30),
            EndTime=datetime.utcnow(),
            Period=2592000,
            Statistics=["Sum" if metric == "Invocations" else "Average"],
        )
        pts = resp.get("Datapoints", [])
        if not pts:
            return 0.0
        key = "Sum" if metric == "Invocations" else "Average"
        return round(pts[0][key], 2)
    except:
        return 0.0

def calculate_cost(memory_mb: int, invocations: int) -> float:
    gb = memory_mb / 1024
    compute = invocations * gb * 0.1 * 0.0000166667
    requests = invocations * 0.0000002
    return round((compute + requests) * settings.PKR_USD_RATE, 2)

def get_functions():
    """Try real AWS, fall back to mock data if credentials not set."""
    if not settings.AWS_ACCESS_KEY_ID:
        return get_mock_functions()
    try:
        client = get_lambda_client()
        fns = client.list_functions().get("Functions", [])
        result = []
        for fn in fns:
            inv = int(get_metric(fn["FunctionName"], "Invocations"))
            dur = get_metric(fn["FunctionName"], "Duration")
            result.append({
                "id": fn["FunctionArn"],
                "name": fn["FunctionName"],
                "region": settings.AWS_REGION,
                "runtime": fn.get("Runtime", "Unknown"),
                "memory": fn["MemorySize"],
                "optimized": fn["MemorySize"],
                "invocations": inv,
                "avgDuration": dur,
                "coldStarts": 0,
                "monthlyCost": calculate_cost(fn["MemorySize"], inv),
                "status": "pending",
                "lastChecked": "Just now",
            })
        return result
    except:
        return get_mock_functions()

def get_mock_functions():
    return [
        {"id": "fn-001", "name": "api-auth-handler", "region": "us-east-1", "runtime": "Node.js 20.x", "memory": 512, "optimized": 256, "invocations": 142000, "avgDuration": 84, "coldStarts": 312, "monthlyCost": 4200, "status": "optimized", "lastChecked": "2 mins ago"},
        {"id": "fn-002", "name": "image-processor", "region": "us-east-1", "runtime": "Python 3.12", "memory": 1024, "optimized": 512, "invocations": 38000, "avgDuration": 612, "coldStarts": 890, "monthlyCost": 8100, "status": "optimized", "lastChecked": "14 mins ago"},
        {"id": "fn-003", "name": "notification-service", "region": "eu-west-1", "runtime": "Node.js 20.x", "memory": 256, "optimized": 128, "invocations": 95000, "avgDuration": 45, "coldStarts": 120, "monthlyCost": 3300, "status": "optimized", "lastChecked": "1 hr ago"},
        {"id": "fn-004", "name": "data-pipeline", "region": "us-east-1", "runtime": "Python 3.12", "memory": 2048, "optimized": 1024, "invocations": 12000, "avgDuration": 1840, "coldStarts": 45, "monthlyCost": 9600, "status": "analyzing", "lastChecked": "In progress"},
        {"id": "fn-005", "name": "report-generator", "region": "ap-south-1", "runtime": "Node.js 20.x", "memory": 768, "optimized": 384, "invocations": 5400, "avgDuration": 320, "coldStarts": 78, "monthlyCost": 1800, "status": "pending", "lastChecked": "3 hrs ago"},
    ]