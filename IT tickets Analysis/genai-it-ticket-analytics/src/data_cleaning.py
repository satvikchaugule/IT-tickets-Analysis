import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from utils import logger, clean_text, parse_date_safe, format_timedelta_hours, write_text_report
from data_loader import (
    load_raw_dataset, save_processed_dataset,
    inspect_dataset, format_inspection_table,
)


REQUIRED_COLUMNS = [
    "Ticket ID",
    "Ticket Type",
    "Ticket Subject",
    "Ticket Description",
    "Ticket Status",
    "Ticket Priority",
    "Ticket Channel",
]


class DataQualityReport:
    def __init__(self):
        self.original_rows = 0
        self.cleaned_rows = 0
        self.duplicates_removed = 0
        self.missing_before = {}
        self.missing_after = {}
        self.invalid_records = 0
        self.records_removed_details = []
        self.records_modified_details = []

    def to_text(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("DATA QUALITY REPORT")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Original rows:                     {self.original_rows}")
        lines.append(f"Duplicates removed:                {self.duplicates_removed}")
        lines.append(f"Invalid/problematic records:       {self.invalid_records}")
        lines.append(f"Final cleaned rows:                {self.cleaned_rows}")
        lines.append(f"Rows retained:                     {self.cleaned_rows}/{self.original_rows} "
                     f"({round(self.cleaned_rows / self.original_rows * 100, 2)}%)"
                     if self.original_rows else "Rows retained: N/A")
        lines.append("")
        if self.records_removed_details:
            lines.append("Removal details:")
            for d in self.records_removed_details:
                lines.append(f"  - {d}")
            lines.append("")
        if self.records_modified_details:
            lines.append("Modification details:")
            for d in self.records_modified_details:
                lines.append(f"  - {d}")
            lines.append("")
        lines.append("Missing value comparison (before -> after):")
        cols = sorted(set(list(self.missing_before.keys()) + list(self.missing_after.keys())))
        lines.append(f"{'Column':<30} {'Before Missing':<15} {'After Missing':<15}")
        lines.append("-" * 65)
        for c in cols:
            b = self.missing_before.get(c, 0)
            a = self.missing_after.get(c, 0)
            lines.append(f"{c:<30} {b:<15} {a:<15}")
        return "\n".join(lines)


def validate_required_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Dataset missing required columns: {missing}. "
            f"Available columns: {list(df.columns)}"
        )


def remove_duplicates(df: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    before = len(df)
    if "Ticket ID" in df.columns:
        dup_mask = df.duplicated(subset=["Ticket ID"], keep="first")
    else:
        dup_mask = df.duplicated(keep="first")
    df_out = df.loc[~dup_mask].copy()
    removed = before - len(df_out)
    report.duplicates_removed = removed
    if removed > 0:
        report.records_removed_details.append(f"Removed {removed} duplicate rows (by Ticket ID if available)")
    logger.info(f"Removed {removed} duplicate rows")
    return df_out


def strip_whitespace_text_columns(df: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    text_cols = df.select_dtypes(include=["object"]).columns.tolist()
    if not text_cols:
        return df
    modified = False
    total_cells = 0
    for col in text_cols:
        before_series = df[col].astype(str)
        df[col] = df[col].apply(lambda x: clean_text(x) if pd.notna(x) else x)
        after_series = df[col].astype(str)
        diffs = (before_series != after_series).sum()
        if diffs > 0:
            total_cells += diffs
            modified = True
    if modified:
        report.records_modified_details.append(
            f"Stripped whitespace / normalized text in {total_cells} cells across {len(text_cols)} text columns"
        )
    return df


def normalize_categoricals(df: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    if "Ticket Priority" in df.columns:
        before = df["Ticket Priority"].astype(str).copy()
        df["Ticket Priority"] = df["Ticket Priority"].apply(
            lambda x: str(x).strip().title() if pd.notna(x) else x
        )
        valid_priorities = {"Low", "Medium", "High", "Critical"}
        invalid_mask = df["Ticket Priority"].notna() & ~df["Ticket Priority"].isin(valid_priorities)
        if invalid_mask.sum() > 0:
            report.records_modified_details.append(
                f"Normalized {invalid_mask.sum()} Ticket Priority values to title-case"
            )
    if "Ticket Status" in df.columns:
        df["Ticket Status"] = df["Ticket Status"].apply(
            lambda x: str(x).strip() if pd.notna(x) else x
        )
    if "Ticket Type" in df.columns:
        df["Ticket Type"] = df["Ticket Type"].apply(
            lambda x: str(x).strip() if pd.notna(x) else x
        )
    if "Ticket Channel" in df.columns:
        df["Ticket Channel"] = df["Ticket Channel"].apply(
            lambda x: str(x).strip() if pd.notna(x) else x
        )
    return df


def parse_dates(df: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    date_cols_map = {
        "Date of Purchase": "purchase_date",
        "First Response Time": "first_response_time",
        "Time to Resolution": "resolution_time",
    }
    for src, dst in date_cols_map.items():
        if src in df.columns:
            parsed = df[src].apply(parse_date_safe)
            failed = df[src].notna() & parsed.isna()
            if failed.sum() > 0:
                report.records_modified_details.append(
                    f"Failed to parse {failed.sum()} values in column '{src}' -> set to NaT"
                )
            df[src] = parsed
    return df


def derive_resolution_metrics(df: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    if "First Response Time" in df.columns and "Time to Resolution" in df.columns:
        df["resolution_time_hours"] = (
            df["Time to Resolution"] - df["First Response Time"]
        ).apply(format_timedelta_hours)

        neg_mask = df["resolution_time_hours"] < 0
        if neg_mask.sum() > 0:
            report.records_modified_details.append(
                f"Found {neg_mask.sum()} negative resolution times; set to NaN"
            )
            df.loc[neg_mask, "resolution_time_hours"] = np.nan
    else:
        df["resolution_time_hours"] = np.nan

    if "Ticket Description" in df.columns:
        df["description_length"] = df["Ticket Description"].apply(
            lambda x: len(clean_text(x))
        )
    else:
        df["description_length"] = 0
    return df


def drop_invalid_rows(df: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    before = len(df)
    mask_valid = pd.Series(True, index=df.index)
    if "Ticket ID" in df.columns:
        mask_valid &= df["Ticket ID"].notna()
    if "Ticket Status" in df.columns:
        mask_valid &= df["Ticket Status"].notna()
    removed = before - mask_valid.sum()
    if removed > 0:
        report.records_removed_details.append(
            f"Removed {removed} rows with missing Ticket ID or Ticket Status"
        )
    report.invalid_records += removed
    return df.loc[mask_valid].copy()


def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, DataQualityReport]:
    report = DataQualityReport()
    report.original_rows = len(df)
    report.missing_before = df.isnull().sum().to_dict()

    validate_required_columns(df)
    logger.info("Starting data cleaning pipeline...")

    df = df.copy()
    df = remove_duplicates(df, report)
    df = strip_whitespace_text_columns(df, report)
    df = normalize_categoricals(df, report)
    df = parse_dates(df, report)
    df = drop_invalid_rows(df, report)
    df = derive_resolution_metrics(df, report)

    report.cleaned_rows = len(df)
    report.missing_after = df.isnull().sum().to_dict()
    logger.info(f"Cleaning complete. Final rows: {len(df)}")
    return df, report


def save_data_quality_report(report: DataQualityReport, inspection_before: dict, inspection_after: dict) -> str:
    content = []
    content.append("=" * 70)
    content.append("RAW DATASET INSPECTION")
    content.append("=" * 70)
    content.append(format_inspection_table(inspection_before))
    content.append("")
    content.append("=" * 70)
    content.append("CLEANED DATASET INSPECTION")
    content.append("=" * 70)
    content.append(format_inspection_table(inspection_after))
    content.append("")
    content.append(report.to_text())
    out = "\n".join(content)
    write_text_report(config.DATA_QUALITY_REPORT, out)
    logger.info(f"Data quality report saved to: {config.DATA_QUALITY_REPORT}")
    return config.DATA_QUALITY_REPORT


def run_cleaning_pipeline() -> tuple[pd.DataFrame, DataQualityReport]:
    raw_df = load_raw_dataset()
    inspection_before = inspect_dataset(raw_df)
    cleaned_df, report = clean_dataset(raw_df)
    inspection_after = inspect_dataset(cleaned_df)
    save_processed_dataset(cleaned_df)
    save_data_quality_report(report, inspection_before, inspection_after)
    return cleaned_df, report


if __name__ == "__main__":
    run_cleaning_pipeline()
