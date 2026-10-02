import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


def setup_logger(name: str = "it_tickets", log_file: str = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


def safe_divide(numerator, denominator, default=0.0):
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except Exception:
        return default


def parse_date_safe(value, errors="coerce"):
    import pandas as pd
    if pd.isna(value):
        return pd.NaT
    try:
        return pd.to_datetime(value, errors=errors)
    except Exception:
        return pd.NaT


def clean_text(text: str) -> str:
    import pandas as pd
    if pd.isna(text):
        return ""
    if not isinstance(text, str):
        return str(text)
    t = text.strip()
    t = " ".join(t.split())
    return t


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def format_timedelta_hours(td):
    import pandas as pd
    if pd.isna(td):
        return None
    try:
        return round(td.total_seconds() / 3600.0, 2)
    except Exception:
        return None


def write_text_report(filepath: str, content: str) -> None:
    ensure_dir(os.path.dirname(filepath))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


logger = setup_logger()
