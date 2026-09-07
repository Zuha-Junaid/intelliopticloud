export const costSummary = {
  previousMonthly: 50000,
  currentMonthly: 18000,
  savedAmount: 32000,
  savingsPercent: 64,
  currency: 'PKR',
}

export const savingsTrend = [
  { month: 'Jul', before: 50000, after: 31000 },
  { month: 'Aug', before: 50000, after: 27000 },
  { month: 'Sep', before: 50000, after: 24000 },
  { month: 'Oct', before: 50000, after: 21000 },
  { month: 'Nov', before: 50000, after: 19000 },
  { month: 'Dec', before: 50000, after: 18000 },
]

export const lambdaFunctions = [
  { id: 'fn-001', name: 'api-auth-handler', region: 'us-east-1', runtime: 'Node.js 20.x', memory: 512, optimized: 256, invocations: 142000, avgDuration: 84, coldStarts: 312, monthlyCost: 4200, status: 'optimized', lastChecked: '2 mins ago' },
  { id: 'fn-002', name: 'image-processor', region: 'us-east-1', runtime: 'Python 3.12', memory: 1024, optimized: 512, invocations: 38000, avgDuration: 612, coldStarts: 890, monthlyCost: 8100, status: 'optimized', lastChecked: '14 mins ago' },
  { id: 'fn-003', name: 'notification-service', region: 'eu-west-1', runtime: 'Node.js 20.x', memory: 256, optimized: 128, invocations: 95000, avgDuration: 45, coldStarts: 120, monthlyCost: 3300, status: 'optimized', lastChecked: '1 hr ago' },
  { id: 'fn-004', name: 'data-pipeline', region: 'us-east-1', runtime: 'Python 3.12', memory: 2048, optimized: 1024, invocations: 12000, avgDuration: 1840, coldStarts: 45, monthlyCost: 9600, status: 'analyzing', lastChecked: 'In progress' },
  { id: 'fn-005', name: 'report-generator', region: 'ap-south-1', runtime: 'Node.js 20.x', memory: 768, optimized: 384, invocations: 5400, avgDuration: 320, coldStarts: 78, monthlyCost: 1800, status: 'pending', lastChecked: '3 hrs ago' },
  { id: 'fn-006', name: 'webhook-dispatcher', region: 'us-east-1', runtime: 'Node.js 20.x', memory: 256, optimized: 256, invocations: 210000, avgDuration: 28, coldStarts: 210, monthlyCost: 2400, status: 'optimized', lastChecked: '5 mins ago' },
  { id: 'fn-007', name: 'invoice-pdf-builder', region: 'eu-west-1', runtime: 'Python 3.12', memory: 1536, optimized: 768, invocations: 8200, avgDuration: 980, coldStarts: 156, monthlyCost: 5200, status: 'analyzing', lastChecked: '22 mins ago' },
]

export const optimizationActions = [
  { id: 1, type: 'Memory Right-Sized', fn: 'api-auth-handler', saving: 4200, time: '2 mins ago', status: 'success' },
  { id: 2, type: 'Spot Instance Switch', fn: 'image-processor', saving: 8100, time: '14 mins ago', status: 'success' },
  { id: 3, type: 'Memory Right-Sized', fn: 'notification-service', saving: 3300, time: '1 hr ago', status: 'success' },
  { id: 4, type: 'Analyzing Workload', fn: 'data-pipeline', saving: null, time: 'In progress', status: 'pending' },
  { id: 5, type: 'Memory Right-Sized', fn: 'report-generator', saving: 1800, time: '3 hrs ago', status: 'success' },
]

export const systemHealth = {
  uptime: '99.98%',
  lastOptimized: '2 mins ago',
  functionsMonitored: 7,
  actionsToday: 12,
}

export const modelInfo = {
  algorithm: 'XGBoost Regressor',
  trainedOn: 'Google Colab',
  trainingSamples: 48200,
  accuracy: 94.2,
  lastTrained: '6 hours ago',
  version: 'v2.3.1',
  features: [
    'Invocation frequency',
    'Memory utilization %',
    'Cold start ratio',
    'Execution duration variance',
    'Time-of-day traffic pattern',
  ],
}

export const optimizationPipeline = [
  { id: 1, stage: 'Data Collection', desc: 'Pulling Lambda metrics from CloudWatch APIs', status: 'complete' },
  { id: 2, stage: 'Feature Engineering', desc: 'Processing usage patterns for model input', status: 'complete' },
  { id: 3, stage: 'XGBoost Prediction', desc: 'Predicting optimal memory & instance config', status: 'complete' },
  { id: 4, stage: 'Decision Validation', desc: 'Simulating cost impact before applying', status: 'complete' },
  { id: 5, stage: 'Zero-Downtime Deployment', desc: 'Applying AWS Lambda configuration update', status: 'active' },
]

export const spotInstanceEvents = [
  { id: 1, fn: 'image-processor', from: 'On-Demand', to: 'Spot', savingPercent: 68, time: '14 mins ago', risk: 'Low' },
  { id: 2, fn: 'data-pipeline', from: 'On-Demand', to: 'Spot', savingPercent: 54, time: '2 hrs ago', risk: 'Medium' },
  { id: 3, fn: 'report-generator', from: 'Spot', to: 'On-Demand', savingPercent: 0, time: '5 hrs ago', risk: 'Reverted (interruption risk)' },
]

export const memoryRightSizingEvents = [
  { id: 1, fn: 'api-auth-handler', from: 512, to: 256, confidence: 96, time: '2 mins ago' },
  { id: 2, fn: 'notification-service', from: 256, to: 128, confidence: 91, time: '1 hr ago' },
  { id: 3, fn: 'report-generator', from: 768, to: 384, confidence: 88, time: '3 hrs ago' },
  { id: 4, fn: 'webhook-dispatcher', from: 256, to: 256, confidence: 99, time: '5 mins ago' },
]