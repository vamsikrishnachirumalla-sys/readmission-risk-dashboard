# paths + settings shared by all the sprint scripts.
# kept in one place so if I move folders around I only fix it here

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
MODELS_DIR = ROOT / "models"

RAW_FILE = RAW_DIR / "diabetic_data.csv"
CLEAN_FILE = PROCESSED_DIR / "encounters_clean.csv"
SCORED_FILE = PROCESSED_DIR / "patients_scored.csv"
MODEL_FILE = MODELS_DIR / "readmission_model.joblib"
METRICS_FILE = REPORTS_DIR / "model_metrics.json"

# id for "Diabetes 130-US Hospitals 1999-2008" on the UCI repo
UCI_DATASET_ID = 296

# discharge codes for patients who passed away or went to hospice.
# they can't come back, so if I leave them in the readmission rate
# looks better than it really is
EXCLUDED_DISCHARGE_IDS = [11, 13, 14, 19, 20, 21]

RANDOM_STATE = 42

for folder in [RAW_DIR, PROCESSED_DIR, REPORTS_DIR, FIGURES_DIR, MODELS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)
