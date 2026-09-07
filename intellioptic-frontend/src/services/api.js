const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchHealthStatus() {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) {
    throw new Error("Failed to connect to backend server");
  }
  return await response.json();
}

export async function fetchFunctionMetrics(functionName) {
  const response = await fetch(`${API_BASE_URL}/api/metrics/${functionName}`);
  if (!response.ok) {
    throw new Error("Failed to fetch CloudWatch metrics");
  }
  return await response.json();
}

export async function triggerOptimization(functionName) {
  const response = await fetch(`${API_BASE_URL}/api/optimize`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ function_name: functionName }),
  });
  if (!response.ok) {
    throw new Error("Failed to process optimization analysis");
  }
  return await response.json();
}