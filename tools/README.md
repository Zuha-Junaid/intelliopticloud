# Tools for the real AWS measurements

These scripts use **no access keys**. Run them in **AWS CloudShell** (the `>_` icon at the top of the AWS console,
region **N. Virginia / us-east-1**). They only create and use functions whose names start with `ioc-demo-`.

| Script | What it does |
|---|---|
| `setup_demo.py` | Creates the role, the 4 demo functions and the permissions for the backend user |
| `collect_benchmark.py` | Measures real durations and memory use at 6 memory sizes -> `real_benchmark.csv` |
| `generate_load.py` | Invokes a demo function many times so there is real usage to measure |
| `train_real.py` | (on your computer) trains the model from `real_benchmark.csv` |

Step-by-step instructions are in the project README, section "Real measurements and verified savings".
