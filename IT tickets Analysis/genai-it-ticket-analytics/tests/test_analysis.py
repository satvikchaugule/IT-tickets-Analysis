import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from analysis import (
    compute_basic_statistics,
    category_analysis,
    priority_analysis,
    status_analysis,
    product_analysis,
    channel_analysis,
    recurring_problems,
)


def _make_df():
    rows = []
    for i in range(1, 11):
        rows.append({
            "Ticket ID": i,
            "Ticket Type": "Technical issue" if i % 3 else "Billing inquiry",
            "Ticket Subject": "Login issue" if i % 2 else "Billing error",
            "Ticket Description": (
                "Cannot login to vpn. Password invalid, network wifi connection down."
                if i % 2 else
                "Billing invoice overcharged duplicate payment."
            ),
            "Ticket Status": "Closed" if i <= 7 else ("Open" if i <= 9 else "Pending Customer Response"),
            "Ticket Priority": (["Critical", "High", "Medium", "Low"] * 3)[:10][i - 1],
            "Ticket Channel": (["Email", "Chat", "Phone", "Social media"] * 3)[:10][i - 1],
            "Product Purchased": (["Laptop A", "Phone B", "Tablet C"] * 4)[:10][i - 1],
            "Customer Name": f"User {i}",
            "Customer Satisfaction Rating": 3.0 + (i % 3),
            "resolution_time_hours": (2.0 * i) if i <= 7 else np.nan,
            "First Response Time": pd.Timestamp("2023-06-01") + pd.Timedelta(days=i),
        })
    return pd.DataFrame(rows)


def test_compute_basic_statistics():
    df = _make_df()
    stats = compute_basic_statistics(df)
    assert stats["total_tickets"] == 10
    assert stats["total_resolved"] == 7
    assert stats["total_unresolved"] == 3
    assert stats["avg_resolution_hours"] is not None
    assert stats["avg_satisfaction"] is not None


def test_category_analysis():
    df = _make_df()
    out = category_analysis(df)
    assert len(out) == 2
    assert "ticket_count" in out.columns
    assert "pct_of_total" in out.columns
    assert "unresolved_pct" in out.columns


def test_priority_analysis():
    df = _make_df()
    out = priority_analysis(df)
    assert len(out) == 4
    assert list(out["Ticket Priority"].head(3)) == ["Critical", "High", "Medium"]


def test_status_analysis():
    df = _make_df()
    out = status_analysis(df)
    assert "ticket_count" in out.columns
    assert len(out) >= 2


def test_product_analysis():
    df = _make_df()
    out = product_analysis(df)
    assert len(out) == 3
    assert "unresolved_pct" in out.columns


def test_channel_analysis():
    df = _make_df()
    out = channel_analysis(df)
    assert len(out) >= 3
    assert "pct_of_total" in out.columns


def test_recurring_problems():
    df = _make_df()
    out = recurring_problems(df, top_n=5)
    assert "top_subjects" in out
    assert "top_types" in out
    assert "top_keywords" in out
    words = [w["word"] for w in out.get("top_keywords", [])]
    assert any(w in words for w in ["billing", "login", "password", "network"])
