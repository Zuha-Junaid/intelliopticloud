# IntelliOptiCloud Free Tier
### A Production-Ready AI System for Autonomous AWS Cost Optimization

**Final Year Project | Department of Software Engineering | The University of Lahore**
**Students:** Zuha Junaid (70135604) · Simra Nadeem (70141978)

---

AI-driven AWS Lambda cost optimization for Pakistani startups and SMEs. It monitors Lambda functions through CloudWatch (metrics and logs), predicts the cheapest memory size with an XGBoost model, can switch a function to Graviton (arm64), applies changes safely with an audit log and rollback, and reports the **measured** saving in PKR.

**Live demo:** https://intellioptic-frontend.vercel.app
**API:** https://intelliopticloud.onrender.com (docs at `/docs`)

> The backend runs on a free Render instance that sleeps after 15 minutes idle. The scheduled GitHub job wakes it every 15 minutes; otherwise the first request can take about 50 seconds.

## Architecture

| Layer | Technology | Hosting (all free) |
|---|---|---|
| Frontend | React (Vite), Tailwind CSS v4, Recharts | Vercel |
| Backend | FastAPI, Uvicorn, JWT auth (bcrypt + python-jose) | Render |
| Database | PostgreSQL (SQLAlchemy); SQLite locally | Neon |
| Monitoring data | CloudWatch metrics and Lambda REPORT log lines via boto3 | AWS Free plan |
| ML | XGBoost regression for memory right-sizing, trained on measured Lambda runs | trained locally from `backend/benchmark/real_benchmark.csv` |
| Scheduler | GitHub Actions (`.github/workflows/monitor.yml`), every 15 minutes | GitHub |
| Source control | Git and GitHub | GitHub |

## What the system does
- **Monitor:** Lambda inventory, invocations and average duration (CloudWatch, 30 days) plus peak memory used and cold-start ratio from the Lambda `REPORT` log lines (7 days). Cost is estimated at AWS list prices from the real duration, memory and architecture.
- **Predict:** XGBoost model with 4 features (memory, average duration, peak memory used, utilisation). The label rule is fixed and documented in `backend/app/services/training.py`: the cheapest size that leaves 25% headroom over peak memory and stays within 25% of the fastest duration.
- **Decide:** memory right-sizing, Graviton (arm64) switch (20% lower price per GB-second) and an advisory "spot suitability" score (AWS Lambda has no spot market).
- **Apply (optional, off by default):** `APPLY_ENABLED=true` on the server, limited to functions named `ioc-demo-*`, three autonomy levels (monitor only / approve / automatic), headroom check, change log and rollback.
- **Verify:** billed cost per invocation before and after each change, from CloudWatch Logs, needs at least 20 invocations on each side.
- **Notify:** recommendations, usage increases, applied changes and a weekly summary, filtered by the user's preferences.
- **History:** one snapshot per function per monitoring cycle in the database.

## API (all under `/api`)
- Public: `POST /auth/register`, `POST /auth/login`
- Token required: `PUT /auth/me`, `/dashboard/summary`, `/resources/functions`, `/optimization/{model-info,pipeline,recommendations,actions}`, `POST /optimization/{apply,rollback/{id},retrain}`, `/reports/{savings,cost-breakdown,history}`, `/notifications`, `/settings`, `/system/status`
- Token **or** `X-Cron-Token`: `POST /system/run-cycle`

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
`backend/.env` (never commit it):
```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
DATABASE_URL=            # empty = local SQLite
SECRET_KEY=              # long random string
APPLY_ENABLED=false      # true allows changing ioc-demo-* functions
APPLY_ALLOWED_PREFIX=ioc-demo-
CRON_TOKEN=              # long random string, same value as the GitHub secret
```

## Tests
```
cd backend
pip install pytest pytest-cov httpx
python -m pytest tests -v
python -m pytest tests --cov=app --cov-branch
```
The tests use a throw-away database and no AWS credentials, whatever is in `.env`.

## Real measurements and verified savings
1. **Create the demo functions** (once): AWS console, CloudShell (region us-east-1), upload the `tools` folder, then `python3 setup_demo.py --user intelliopticloud-app`.
2. **Collect the benchmark:** `python3 collect_benchmark.py --output real_benchmark.csv` (10-20 minutes), download the file and save it as `backend/benchmark/real_benchmark.csv`.
3. **Train:** from the project root `python tools/train_real.py` (writes `backend/app/model/*` and `backend/benchmark/training_report.json`), commit and push.
4. **Turn on applying:** in Render set `APPLY_ENABLED=true` and `CRON_TOKEN=<random>`; in GitHub add the secret `CRON_TOKEN` with the same value.
5. **Verify a saving:** `python3 generate_load.py --function ioc-demo-api --count 150` in CloudShell, then in the app press Apply on `ioc-demo-api`, run the load again, and open Reports.

## Limitations
- Training data are **measured benchmark workloads** (memory held x CPU work x waiting time) run on real AWS Lambda, not the production functions of real customers. The held-out accuracy in `training_report.json` measures how well the model generalises to unseen workloads of this benchmark.
- Costs are **list-price estimates**. The AWS Free plan means the test account is not billed for them.
- Applying changes is limited to `ioc-demo-*` functions and to the six memory sizes 128, 256, 512, 1024, 2048 and 3008 MB.
- The 15-minute schedule depends on GitHub Actions, which can delay or skip scheduled runs.
- The AWS Free plan used for testing expires around April 2027.
