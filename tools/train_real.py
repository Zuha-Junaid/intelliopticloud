"""Train the memory model on the real benchmark and write the model files used by the backend.

Run from the project root:
    python tools/train_real.py backend/benchmark/real_benchmark.csv
With extra measurements, give several files; they are merged into the FIRST file and the model is trained on all:
    python tools/train_real.py backend/benchmark/real_benchmark.csv backend/benchmark/real_benchmark_extra.csv
It writes backend/app/model/memory_model.json and model_meta.json and backend/benchmark/training_report.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.services import training  # noqa: E402


def main():
    files = [Path(a) for a in sys.argv[1:]] or [ROOT / "backend" / "benchmark" / "real_benchmark.csv"]
    csv_path = files[0]
    if len(files) > 1:
        n = training.merge_csvs(files, csv_path)
        print(f"Merged {len(files)} files into {csv_path} ({n} measurements)")
    model_dir = ROOT / "backend" / "app" / "model"
    meta = training.train_from_csv(csv_path, model_dir / "memory_model.json", model_dir / "model_meta.json")
    (ROOT / "backend" / "benchmark" / "training_report.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: v for k, v in meta.items() if k != "held_out_detail"}, indent=2))


if __name__ == "__main__":
    main()
