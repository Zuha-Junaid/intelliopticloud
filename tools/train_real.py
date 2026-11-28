"""Train the memory model on the real benchmark and write the model files used by the backend.

Run from the project root:
    python tools/train_real.py backend/benchmark/real_benchmark.csv
It writes backend/app/model/memory_model.json and model_meta.json and backend/benchmark/training_report.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.services import training  # noqa: E402


def main():
    csv_path = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "backend" / "benchmark" / "real_benchmark.csv")
    model_dir = ROOT / "backend" / "app" / "model"
    meta = training.train_from_csv(csv_path, model_dir / "memory_model.json", model_dir / "model_meta.json")
    (ROOT / "backend" / "benchmark" / "training_report.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: v for k, v in meta.items() if k != "held_out_detail"}, indent=2))


if __name__ == "__main__":
    main()
