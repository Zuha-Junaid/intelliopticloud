# IntelliOptiCloud Free Tier
### A Production-Ready AI System for Autonomous AWS Cost Optimization

**Final Year Project | Department of Software Engineering | The University of Lahore**
**Students:** Zuha Junaid (70135604) · Simra Nadeem (70141978)

---

AI-driven AWS Lambda cost optimization for Pakistani startups and SMEs. It monitors Lambda functions through CloudWatch, recommends right-sized memory with an XGBoost model, and shows costs in PKR.

**Live demo:** https://intellioptic-frontend.vercel.app
**API:** https://intelliopticloud.onrender.com (docs at `/docs`)

> The backend runs on a free Render instance that sleeps after 15 minutes idle. The first request after a pause can take about 50 seconds.


## Architecture

| Layer | Technology | Hosting (all free) |
|---|---|---|
| Frontend | React (Vite), Tailwind CSS v4, Recharts | Vercel |
| Backend | FastAPI, Uvicorn, JWT auth (bcrypt + python-jose) | Render |
| Database | PostgreSQL (SQLAlchemy); SQLite locally | Neon |
| Monitoring data | AWS CloudWatch and Lambda via boto3 (read-only IAM user) | AWS Free plan |
| ML | XGBoost regression for memory right-sizing | trained in Google Colab / at backend startup |
| Source control | Git and GitHub | GitHub |

Browser (Vercel) -> FastAPI (Render) -> Neon Postgres (accounts), AWS CloudWatch/Lambda (metrics), XGBoost (recommendations).

## Features
- Register, login and protected routes. JWT is verified on every data endpoint.
- Real Lambda inventory, invocations and average duration from CloudWatch (last 30 days). Falls back to mock data if AWS credentials are missing.
- Memory right-sizing recommendations from an XGBoost model, with confidence scores.
- Spot-instance suitability recommendations.
- Cost figures in PKR (rate configurable, default 278 PKR/USD).
- Dashboard, resources, optimization pipeline, reports and notifications pages, responsive on mobile, tablet and desktop.

## API (all under `/api`)
- Public: `POST /auth/register`, `POST /auth/login`
- Require `Authorization: Bearer <token>`: `/dashboard/summary`, `/resources/functions`, `/optimization/model-info`, `/optimization/pipeline`, `/optimization/recommendations`, `/optimization/retrain`, `/reports/savings`, `/reports/cost-breakdown`, `/notifications`

## Run locally

Backend:
```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Frontend:
```
cd intellioptic-frontend
npm install
npm run dev
```
Create `backend/.env` (never commit it):
```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
DATABASE_URL=            # empty = local SQLite
SECRET_KEY=              # long random string
```

## Limitations 
- **The model is trained on synthetic data.** No real labelled dataset of Lambda right-sizing outcomes exists. The reported accuracy (99.7%) shows the model learns the generating rule; it is not a measure of real-world savings.
- The 6-month savings chart on the dashboard is **sample data** for illustration. Savings are reported as 0 until optimizations are applied.
- The system recommends changes; it does not yet apply them to AWS automatically (autonomous execution is Phase 2).
- The test AWS account runs only a few small Lambda functions, so real costs are near PKR 0.
- The AWS Free plan used for testing expires around April 2027.

