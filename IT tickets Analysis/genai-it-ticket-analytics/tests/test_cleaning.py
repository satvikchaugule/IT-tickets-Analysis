import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from data_cleaning import (
    clean_dataset,
    remove_duplicates,
    strip_whitespace_text_columns,
    normalize_categoricals,
    parse_dates,
    derive_resolution_metrics,
    drop_invalid_rows,
    validate_required_columns,
    DataQualityReport,
)
from utils import clean_text, parse_date_safe, safe_divide


def _make_sample_df():
    return pd.DataFrame([
        {
            "Ticket ID": 1, "Customer Name": " Alice ", "Customer Email": "a@x.com",
            "Customer Age": 30, "Customer Gender": "Female",
            "Product Purchased": "Laptop A", "Date of Purchase": "2023-01-05",
            "Ticket Type": " Technical issue ", "Ticket Subject": "Cannot login ",
            "Ticket Description": "  My password is not working.  ",
            "Ticket Status": " Open ", "Resolution": "", "Ticket Priority": " high ",
            "Ticket Channel": "Email",
            "First Response Time": "2023-06-01 10:00:00",
            "Time to Resolution": "2023-06-01 14:30:00",
            "Customer Satisfaction Rating": 4.0,
        },
        {
            "Ticket ID": 1, "Customer Name": "Alice", "Customer Email": "a@x.com",
            "Customer Age": 30, "Customer Gender": "Female",
            "Product Purchased": "Laptop A", "Date of Purchase": "2023-01-05",
            "Ticket Type": "Technical issue", "Ticket Subject": "Cannot login",
            "Ticket Description": "Duplicate row.",
            "Ticket Status": "Open", "Resolution": "", "Ticket Priority": "High",
            "Ticket Channel": "Email",
            "First Response Time": "2023-06-01 10:00:00",
            "Time to Resolution": "2023-06-01 14:30:00",
            "Customer Satisfaction Rating": 4.0,
        },
        {
            "Ticket ID": 2, "Customer Name": "Bob", "Customer Email": "b@x.com",
            "Customer Age": 45, "Customer Gender": "Male",
            "Product Purchased": "Phone B", "Date of Purchase": "2023-02-10",
            "Ticket Type": "Billing inquiry", "Ticket Subject": "Overcharged",
            "Ticket Description": "I was billed twice this month.",
            "Ticket Status": "Closed", "Resolution": "Refund issued", "Ticket Priority": "low",
            "Ticket Channel": "Chat",
            "First Response Time": "2023-06-02 08:00:00",
            "Time to Resolution": "2023-06-02 07:30:00",
            "Customer Satisfaction Rating": 5.0,
        },
        {
            "Ticket ID": None, "Customer Name": "NoID", "Customer Email": "n@x.com",
            "Customer Age": 25, "Customer Gender": "Other",
            "Product Purchased": "Tablet C", "Date of Purchase": "bad-date",
            "Ticket Type": "Refund request", "Ticket Subject": "Broken screen",
            "Ticket Description": "Screen cracked on arrival.",
            "Ticket Status": None, "Resolution": "", "Ticket Priority": "Critical",
            "Ticket Channel": "Phone",
            "First Response Time": "not-a-date",
            "Time to Resolution": None,
            "Customer Satisfaction Rating": np.nan,
        },
    ])


def test_clean_text_basic():
    assert clean_text("  hello   world  ") == "hello world"
    assert clean_text(np.nan) == ""
    assert clean_text(None) == ""


def test_safe_divide():
    assert safe_divide(10, 2) == 5.0
    assert safe_divide(1, 0) == 0.0
    assert safe_divide(None, 2) == 0.0


def test_parse_date_safe():
    import pandas as pd
    assert pd.notna(parse_date_safe("2023-06-01 10:00:00"))
    assert pd.isna(parse_date_safe("not-a-date"))
    assert pd.isna(parse_date_safe(np.nan))


def test_validate_required_columns_ok():
    df = _make_sample_df()
    validate_required_columns(df)


def test_validate_required_columns_missing():
    df = _make_sample_df().drop(columns=["Ticket Priority"])
    with pytest.raises(ValueError):
        validate_required_columns(df)


def test_remove_duplicates():
    df = _make_sample_df()
    report = DataQualityReport()
    out = remove_duplicates(df, report)
    assert report.duplicates_removed == 1
    assert len(out) == 3


def test_strip_whitespace_text_columns():
    df = _make_sample_df()
    report = DataQualityReport()
    out = strip_whitespace_text_columns(df, report)
    assert out.loc[0, "Customer Name"] == "Alice"
    assert out.loc[0, "Ticket Type"] == "Technical issue"


def test_normalize_categoricals():
    df = _make_sample_df()
    report = DataQualityReport()
    out = normalize_categoricals(df, report)
    assert out.loc[0, "Ticket Priority"] == "High"
    assert out.loc[2, "Ticket Priority"] == "Low"


def test_parse_dates():
    df = _make_sample_df()
    report = DataQualityReport()
    out = parse_dates(df, report)
    assert pd.api.types.is_datetime64_any_dtype(out["First Response Time"])
    assert pd.isna(out.loc[3, "First Response Time"])


def test_drop_invalid_rows():
    df = _make_sample_df()
    report = DataQualityReport()
    out = drop_invalid_rows(df, report)
    assert report.invalid_records >= 1
    assert len(out) == 3


def test_derive_resolution_metrics_negative():
    df = _make_sample_df()
    report = DataQualityReport()
    df = parse_dates(df, report)
    out = derive_resolution_metrics(df, report)
    assert out.loc[0, "resolution_time_hours"] == 4.5
    assert np.isnan(out.loc[2, "resolution_time_hours"])


def test_clean_dataset_end_to_end():
    df = _make_sample_df()
    cleaned, report = clean_dataset(df)
    assert report.original_rows == 4
    assert report.duplicates_removed == 1
    assert report.cleaned_rows <= 3
    assert "resolution_time_hours" in cleaned.columns
    assert "description_length" in cleaned.columns
