import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from utils import logger, clean_text, ensure_dir


def find_raw_dataset():
    candidates = [
        config.RAW_DATA_FILE,
        os.path.join(config.RAW_DATA_DIR, "customer_support_tickets.csv"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    for ext in ("*.csv", "*.xlsx", "*.xls"):
        import glob
        matches = glob.glob(os.path.join(config.RAW_DATA_DIR, ext))
        if matches:
            return sorted(matches)[0]
    return None


def load_raw_dataset(filepath: str = None) -> pd.DataFrame:
    if filepath is None:
        filepath = find_raw_dataset()
    if filepath is None or not os.path.isfile(filepath):
        raise FileNotFoundError(
            f"Raw dataset not found. Expected at {config.RAW_DATA_FILE}. "
            f"Please place a CSV/Excel file in {config.RAW_DATA_DIR}."
        )
    logger.info(f"Loading raw dataset from: {filepath}")
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".xlsx", ".xls", ".xlsm"):
        df = pd.read_excel(filepath)
    elif ext == ".csv":
        try:
            df = pd.read_csv(filepath)
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding="latin-1")
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    logger.info(f"Loaded dataset shape: {df.shape}")
    return df


def load_processed_dataset() -> pd.DataFrame:
    if not os.path.isfile(config.PROCESSED_DATA_FILE):
        raise FileNotFoundError(
            f"Processed dataset not found at {config.PROCESSED_DATA_FILE}. "
            f"Run the cleaning pipeline first."
        )
    df = pd.read_csv(config.PROCESSED_DATA_FILE, parse_dates=_date_columns())
    logger.info(f"Loaded processed dataset shape: {df.shape}")
    return df


def _date_columns():
    return [
        "Date of Purchase", "First Response Time", "Time to Resolution",
        "created_date_parsed", "resolved_date_parsed",
    ]


def save_processed_dataset(df: pd.DataFrame) -> str:
    ensure_dir(config.PROCESSED_DATA_DIR)
    df.to_csv(config.PROCESSED_DATA_FILE, index=False)
    logger.info(f"Saved processed dataset to: {config.PROCESSED_DATA_FILE} (rows={len(df)})")
    return config.PROCESSED_DATA_FILE


def inspect_dataset(df: pd.DataFrame) -> dict:
    report = {}
    report["shape"] = df.shape
    report["columns"] = list(df.columns)
    report["dtypes"] = df.dtypes.astype(str).to_dict()
    report["missing"] = df.isnull().sum().to_dict()
    report["missing_pct"] = (df.isnull().sum() / len(df) * 100).round(2).to_dict()
    report["duplicates"] = int(df.duplicated().sum())
    report["nunique"] = df.nunique(dropna=True).to_dict()
    try:
        report["memory_mb"] = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
    except Exception:
        report["memory_mb"] = None
    return report


def format_inspection_table(report: dict) -> str:
    lines = []
    lines.append(f"Dataset Shape: {report['shape'][0]} rows x {report['shape'][1]} columns")
    lines.append(f"Duplicate rows: {report['duplicates']}")
    if report.get("memory_mb") is not None:
        lines.append(f"Memory usage: {report['memory_mb']} MB")
    lines.append("")
    lines.append(f"{'Column':<30} {'Dtype':<15} {'Missing %':<10} {'Unique':<10} Notes")
    lines.append("-" * 90)
    for col in report["columns"]:
        dtype = report["dtypes"].get(col, "")
        mpct = report["missing_pct"].get(col, 0)
        uniq = report["nunique"].get(col, 0)
        notes = []
        if mpct > 0:
            notes.append(f"missing={report['missing'].get(col,0)}")
        if uniq == report["shape"][0]:
            notes.append("unique_key")
        elif uniq <= 10:
            notes.append("low_cardinality")
        lines.append(f"{col:<30} {dtype:<15} {mpct:<10} {uniq:<10} {'; '.join(notes)}")
    return "\n".join(lines)
