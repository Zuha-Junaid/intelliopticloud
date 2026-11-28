# IntelliOptiCloud Free Tier
### AI-Driven AWS Lambda Cost Optimization (monitor, recommend, apply, verify)

**Final Year Project | Department of Software Engineering | The University of Lahore**
**Students:** Zuha Junaid (70135604) · Simra Nadeem (70141978) | **Advisor:** Miss Sana Munir | **Project ID:** FYP-F25-11

---

IntelliOptiCloud monitors AWS Lambda functions through CloudWatch (metrics and logs), predicts the cheapest safe memory size with an XGBoost model, can switch a function to Graviton (arm64), applies changes safely with an audit log and rollback, **measures** the real saving from billed durations, and rolls a change back when it made things worse. Everything runs on free tools.

**Live demo:** https://intellioptic-frontend.vercel.app
**API:** https://intelliopticloud.onrender.com (docs at `/docs`)

> The backend runs on a free Render instance that sleeps after 15 minutes idle. The scheduled GitHub job wakes it every 15 minutes; otherwise the first request can take about 50 seconds.

## Architecture

| Layer | Technology | Hosting (all free) |
|---|---|---|
| Frontend | React (Vite), Tailwind CSS v4, Recharts | Vercel |
| Backend | FastAPI, Uvicorn, JWT auth (bcrypt + python-jose) | Render |
| Database | PostgreSQL (SQLAlchemy); SQLite locally | Neon |
| Monitoring data | CloudWatch metrics and Lambda `REPORT` log lines via boto3 | AWS Free plan |
| ML | XGBoost regression for memory right-sizing, trained on 96 measured Lambda workloads | trained locally from `backend/benchmark/real_benchmark.csv` |
| Scheduler | GitHub Actions (`.github/workflows/monitor.yml`), every 15 minutes | GitHub |
| Source control | Git and GitHub | GitHub |

## Project structure
```
backend/
  app/
    routers/      auth, dashboard, resources, optimization, reports, notifications, system
    services/     cloudwatch_service   CloudWatch metrics + REPORT log parsing, cost formula
                  optimizer_service    model loading, memory / arm64 / spot recommendations
                  training             benchmark CSV -> labels -> model, cross-validation
                  apply_service        applies and rolls back changes (all safety rules)
                  savings_service      verified saving from billed cost before / after
                  guard_service        judges each change by measured cost and speed, auto-rollback
                  cycle_service        one monitoring cycle (read, store, recommend, apply, guard)
                  store                settings, notifications, action log
    model/        memory_model.json + model_meta.json (the trained model)
  benchmark/      real_benchmark.csv (measured data) + training_report.json (metrics)
  tests/          pytest suite (144 tests)
intellioptic-frontend/   React app (Dashboard, Resources, Optimization, Reports, Notifications, Settings)
tools/                   scripts that run in AWS CloudShell or train the model (no access keys needed)
.github/workflows/       monitor.yml (15-minute cycle)
```

## What the system does
- **Monitor:** Lambda inventory, invocations and average duration (CloudWatch, 30 days) plus peak memory used and cold-start ratio from the Lambda `REPORT` log lines (7 days). Cost is estimated at AWS list prices from the real billed duration, memory and architecture (no fixed-duration assumption).
- **Predict:** XGBoost model with 4 features (memory, average duration, peak memory used, utilisation). The label rule is fixed and documented in `backend/app/services/training.py`: the cheapest size that leaves 25% headroom over peak memory and stays within 25% of the fastest duration. The backend never recommends a size below the minimum safe size for the measured peak memory, and as a cost optimiser it shows a larger size only when the current one is too small for the measured peak memory.
- **Decide:** memory right-sizing, Graviton (arm64) switch (20% lower price per GB-second) and an advisory "spot suitability" score (AWS Lambda has no spot market, so Graviton is the option that can really be applied).
- **Apply (optional, off by default):** `APPLY_ENABLED=true` on the server, limited to functions named `ioc-demo-*`, three autonomy levels (monitor only / approve / automatic), 25% headroom check, refusal when no peak memory has been measured, change log and rollback. A *Try a size* control on the Optimization page lets the user run a manual memory experiment (any size that keeps the headroom); Reports then measures the real result.
- **Verify:** billed cost per invocation before and after each change, from CloudWatch Logs; at least 20 invocations are needed on each side. Each change is measured only against its own period.
- **Guard (closed loop):** once a change has enough new invocations, its measured result is judged: the cost per invocation must not rise by more than 5% and the average billed duration must not be more than 25% slower. A change that fails is reported ("Change made things worse"); only in the *automatic* level the system rolls it back ("Automatic rollback") and tells the user. Every change is judged once.
- **Notify:** recommendations, usage increases, applied and verified changes, rollbacks and a weekly summary, filtered by the user's preferences.
- **History:** one snapshot per function per monitoring cycle in the database.
- **Honest labels:** when AWS is not connected the app shows clearly marked sample data and never stores it as history.

## Measured results (from this project's own AWS account)

**Verified saving.** `ioc-demo-api` was moved from x86_64 to arm64 by the system. Measured from 150 invocations before and 150 after: cost per invocation 0.000908 PKR to 0.000737 PKR, **18.8% lower** (the list-price difference is 20%). The monthly amount in PKR is very small because the demo function has little traffic; the percentage is the meaningful number.

**Model** (`backend/benchmark/training_report.json`, version v3.1): trained on **96 measured workloads** (36 base + 60 extra, each at up to 6 memory sizes = 422 measurements) from AWS Lambda.

| Measure | Result |
|---|---|
| Held-out split (28 unseen workloads): exact size / within one step | 45.7% / 92.1% |
| Unsafe predictions (below the minimum safe size) | 0 |
| Cross-validation (6 folds x 3 repeats, grouped by workload): exact / within one step | 58.8% / 87.4% |
| Memory-reducing recommendations that cut cost by more than 2% | 97.8% |
| ... of which made the function more than 25% slower | 25.0% |
| Mean cost change of those recommendations | -32.3% |

Comparison with two trivial rules, on the same cross-validation:

| Rule | Cut cost | More than 25% slower | Mean cost change |
|---|---|---|---|
| Model | 97.8% | 25.0% | -32.3% |
| Shrink to the minimum safe size | 82.8% | 81.4% | -35.5% |
| Always 2048 MB (never below the safe size) | 98.8% | 9.3% | -28.9% |

How to read this: the model is far better than the naive "shrink to the minimum safe size" rule, which makes four out of five functions much slower. Against "always 2048 MB" the model finds more savings (-32.3% instead of -28.9%, on 104 instead of 86 scored recommendations) but slows a function down more often (25.0% instead of 9.3%). One observation of a function (memory, duration, peak memory) cannot tell CPU-bound code from waiting-bound code, so a better model needs more information, not more of the same data. That is why the guard exists: a wrong recommendation is measured and can be rolled back. A variant that rounds predictions up to the next size was also tested: it lowered the slow-down rate to 17.1% but halved the number of recommendations, so it was not adopted.

Data quality note: Lambda reports "Max Memory Used" as the highest value of a whole reused execution environment. The benchmark therefore runs small workloads first and training uses the lowest peak measured for each workload. An earlier extra run in random order had inflated peaks (45 of 60 workloads) and gave 41.7% accuracy and 22 unsafe predictions; it was discarded and re-measured.

The earlier figure of 99.7% accuracy belonged to a model trained on synthetic data and only showed that the model had learned the rule used to create that data. It is not used any more.

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
Never commit `.env` or the access-key CSV file. Keep both in `.gitignore`.

## Tests
```
cd backend
pip install pytest pytest-cov httpx
python -m pytest tests -v
python -m pytest tests --cov=app --cov-branch
```
144 tests, 95% line and branch coverage. The tests use a throw-away database, a simulated AWS (no network) and no credentials, whatever is in `.env`. They do not depend on which model file is shipped: tests that need a fixed recommendation set it themselves, and the model state is restored after every test.

## Real measurements and verified savings
All AWS steps run in **AWS CloudShell** (the `>_` icon in the AWS console, region N. Virginia / us-east-1) and need no access keys.
1. **Create the demo functions** (once): upload the files of the `tools` folder to CloudShell (`demo_handler.py`, `setup_demo.py`, `collect_benchmark.py`, `generate_load.py`), then `python3 setup_demo.py --user intelliopticloud-app`.
2. **Collect the benchmark:** `python3 collect_benchmark.py --output real_benchmark.csv` (10-20 minutes), download the file and save it as `backend/benchmark/real_benchmark.csv`.
2b. **More workloads (recommended, 20-30 minutes):** `python3 collect_benchmark.py --extra 60 --output real_benchmark_extra.csv` (60 new workloads; if CloudShell disconnects, run the same command again and it continues). Download it into `backend/benchmark/` and train on both files: `python tools/train_real.py backend/benchmark/real_benchmark.csv backend/benchmark/real_benchmark_extra.csv`.
3. **Train:** from the project root `python tools/train_real.py` (writes `backend/app/model/*` and `backend/benchmark/training_report.json`), run the tests, commit and push. Render then uses the new model.
4. **Turn on applying and the schedule:** in Render set `APPLY_ENABLED=true` and `CRON_TOKEN=<random>`; in GitHub add the secret `CRON_TOKEN` with the same value; in the Actions tab run **Monitoring cycle** once by hand (green tick).
5. **Verify a saving:** `python3 generate_load.py --function ioc-demo-api --count 150` in CloudShell, then in the app open Optimization, press Apply on the function, run the same load again, and open Reports.
6. **Try the guard (optional):** in Settings set the autonomy level to Automatic, run a cycle, and read the Notifications ("Change verified" or "Automatic rollback"). Set it back to Approval afterwards.

## Troubleshooting
- **Apply is refused:** `APPLY_ENABLED` is not `true` in Render, the autonomy level is "Monitor only", the function name does not start with `ioc-demo-`, or no peak memory has been measured yet (run the load script first and press *Run Cycle Now*).
- **Reports shows "waiting for usage":** a change needs at least 20 invocations before and after it. Each change is measured only until the next change on the same function, so after every change run the load script (or let real traffic arrive) **before** making another change to that function; otherwise the first change can never be verified.
- **The app says sample data:** AWS credentials are missing or wrong in Render; the app then shows labelled sample data and applies nothing.
- **Actions run fails with 401:** the `CRON_TOKEN` secret in GitHub is different from the one in Render.
- **No automatic runs appear in the Actions tab:** GitHub can delay scheduled runs of a new workflow by hours. Plan B (free): create a job at cron-job.org that sends `POST https://intelliopticloud.onrender.com/api/system/run-cycle` every 15 minutes with the header `X-Cron-Token: <your CRON_TOKEN>`.
- **Benchmark peak memory looks too high:** Lambda reports "Max Memory Used" as the highest value of a whole reused execution environment. The benchmark therefore runs small workloads first, and training uses the lowest peak measured for each workload (`harmonise_peaks` in `training.py`).
- **First page load is slow:** the free Render server was asleep.

## Limitations
- The model sees **one observation** of a function (memory, duration, peak memory), so it cannot tell CPU-bound from waiting-bound code. `training_report.json` therefore reports a workload-grouped cross-validation and compares the model with two trivial baselines; the guard above limits the cost of a wrong prediction.
- Training data are **measured benchmark workloads** (memory held x CPU work x waiting time) run on real AWS Lambda, not the production functions of real customers. The accuracy figures measure how well the model generalises to unseen workloads of this benchmark; the test set is small (28 workloads).
- AWS Lambda has **no spot market**. The "spot" score is advisory only; the applicable cheaper option is Graviton (arm64).
- Costs are **list-price estimates**. The AWS Free plan means the test account is not billed for them. The verified saving is measured on a demo function with little traffic.
- Applying changes is limited to `ioc-demo-*` functions and to the six memory sizes 128, 256, 512, 1024, 2048 and 3008 MB. Container-image functions are not switched to arm64.
- The 15-minute schedule depends on GitHub Actions, which can delay or skip scheduled runs.
- The AWS Free plan used for testing expires around April 2027.
