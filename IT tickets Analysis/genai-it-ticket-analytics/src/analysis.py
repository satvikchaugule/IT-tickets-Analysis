import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from utils import logger, safe_divide, ensure_dir, write_text_report, clean_text


def compute_basic_statistics(df: pd.DataFrame) -> dict:
    stats = {}
    stats["total_tickets"] = len(df)
    stats["total_ticket_types"] = df["Ticket Type"].nunique() if "Ticket Type" in df else 0
    stats["total_products"] = df["Product Purchased"].nunique() if "Product Purchased" in df else 0
    stats["total_customers"] = df["Customer Name"].nunique() if "Customer Name" in df else 0
    stats["total_channels"] = df["Ticket Channel"].nunique() if "Ticket Channel" in df else 0

    if "Ticket Status" in df.columns:
        resolved_aliases = {"Closed", "Resolved"}
        unresolved_aliases = {"Open", "Pending Customer Response", "In Progress", "Pending"}
        status_lower = df["Ticket Status"].str.strip().str.lower()
        resolved_mask = df["Ticket Status"].isin(resolved_aliases) | status_lower.isin([s.lower() for s in resolved_aliases])
        unresolved_mask = df["Ticket Status"].isin(unresolved_aliases) | status_lower.isin([s.lower() for s in unresolved_aliases])
        stats["total_resolved"] = int(resolved_mask.sum())
        stats["total_unresolved"] = int(unresolved_mask.sum())
        stats["total_open"] = int((df["Ticket Status"] == "Open").sum())
    else:
        stats["total_resolved"] = 0
        stats["total_unresolved"] = 0
        stats["total_open"] = 0

    rth = df.get("resolution_time_hours", pd.Series(dtype="float64")).dropna()
    if len(rth) > 0:
        stats["avg_resolution_hours"] = round(float(rth.mean()), 2)
        stats["median_resolution_hours"] = round(float(rth.median()), 2)
        stats["min_resolution_hours"] = round(float(rth.min()), 2)
        stats["max_resolution_hours"] = round(float(rth.max()), 2)
    else:
        for k in ["avg_resolution_hours", "median_resolution_hours", "min_resolution_hours", "max_resolution_hours"]:
            stats[k] = None

    csr = df.get("Customer Satisfaction Rating", pd.Series(dtype="float64")).dropna()
    if len(csr) > 0:
        stats["avg_satisfaction"] = round(float(csr.mean()), 2)
    else:
        stats["avg_satisfaction"] = None
    return stats


def _is_unresolved(s: pd.Series) -> int:
    if s.dtype != object:
        return 0
    norm = s.fillna("").astype(str).str.strip().str.lower()
    return int((~norm.isin(["closed", "resolved"])).sum())


def category_analysis(df: pd.DataFrame) -> pd.DataFrame:
    if "Ticket Type" not in df.columns:
        return pd.DataFrame()
    grp = df.groupby("Ticket Type", dropna=False)
    out = grp.agg(
        ticket_count=("Ticket ID", "count") if "Ticket ID" in df else ("Ticket Type", "count"),
        avg_resolution_hours=("resolution_time_hours", "mean"),
        median_resolution_hours=("resolution_time_hours", "median"),
        unresolved_count=("Ticket Status", _is_unresolved),
    ).reset_index()
    out["pct_of_total"] = (out["ticket_count"] / out["ticket_count"].sum() * 100).round(2)
    out["unresolved_pct"] = (out["unresolved_count"] / out["ticket_count"] * 100).round(2)
    out["avg_resolution_hours"] = out["avg_resolution_hours"].round(2)
    out["median_resolution_hours"] = out["median_resolution_hours"].round(2)
    out = out.sort_values("ticket_count", ascending=False).reset_index(drop=True)
    return out


def priority_analysis(df: pd.DataFrame) -> pd.DataFrame:
    if "Ticket Priority" not in df.columns:
        return pd.DataFrame()
    grp = df.groupby("Ticket Priority", dropna=False)
    out = grp.agg(
        ticket_count=("Ticket ID", "count") if "Ticket ID" in df else ("Ticket Priority", "count"),
        avg_resolution_hours=("resolution_time_hours", "mean"),
        unresolved_count=("Ticket Status", _is_unresolved),
    ).reset_index()
    out["pct_of_total"] = (out["ticket_count"] / out["ticket_count"].sum() * 100).round(2)
    out["unresolved_pct"] = (out["unresolved_count"] / out["ticket_count"] * 100).round(2)
    out["avg_resolution_hours"] = out["avg_resolution_hours"].round(2)
    priority_order = ["Critical", "High", "Medium", "Low"]
    out["sort_key"] = out["Ticket Priority"].apply(
        lambda x: priority_order.index(x) if x in priority_order else 99
    )
    out = out.sort_values("sort_key").drop(columns=["sort_key"]).reset_index(drop=True)
    return out


def status_analysis(df: pd.DataFrame) -> pd.DataFrame:
    if "Ticket Status" not in df.columns:
        return pd.DataFrame()
    out = df.groupby("Ticket Status", dropna=False).agg(
        ticket_count=("Ticket ID", "count") if "Ticket ID" in df else ("Ticket Status", "count"),
        avg_resolution_hours=("resolution_time_hours", "mean"),
    ).reset_index()
    out["pct_of_total"] = (out["ticket_count"] / out["ticket_count"].sum() * 100).round(2)
    out["avg_resolution_hours"] = out["avg_resolution_hours"].round(2)
    out = out.sort_values("ticket_count", ascending=False).reset_index(drop=True)
    return out


def product_analysis(df: pd.DataFrame) -> pd.DataFrame:
    if "Product Purchased" not in df.columns:
        return pd.DataFrame()
    grp = df.groupby("Product Purchased", dropna=False)
    out = grp.agg(
        ticket_count=("Ticket ID", "count") if "Ticket ID" in df else ("Product Purchased", "count"),
        avg_resolution_hours=("resolution_time_hours", "mean"),
        avg_satisfaction=("Customer Satisfaction Rating", "mean"),
        unresolved_count=("Ticket Status", _is_unresolved),
    ).reset_index()
    out["avg_resolution_hours"] = out["avg_resolution_hours"].round(2)
    out["avg_satisfaction"] = out["avg_satisfaction"].round(2)
    out["unresolved_pct"] = (out["unresolved_count"] / out["ticket_count"] * 100).round(2)
    out = out.sort_values("ticket_count", ascending=False).reset_index(drop=True)
    return out


def channel_analysis(df: pd.DataFrame) -> pd.DataFrame:
    if "Ticket Channel" not in df.columns:
        return pd.DataFrame()
    grp = df.groupby("Ticket Channel", dropna=False)
    out = grp.agg(
        ticket_count=("Ticket ID", "count") if "Ticket ID" in df else ("Ticket Channel", "count"),
        avg_resolution_hours=("resolution_time_hours", "mean"),
    ).reset_index()
    out["pct_of_total"] = (out["ticket_count"] / out["ticket_count"].sum() * 100).round(2)
    out["avg_resolution_hours"] = out["avg_resolution_hours"].round(2)
    out = out.sort_values("ticket_count", ascending=False).reset_index(drop=True)
    return out


def time_analysis(df: pd.DataFrame) -> dict:
    result = {}
    date_col = None
    for c in ["First Response Time", "Date of Purchase", "Time to Resolution"]:
        if c in df.columns and df[c].notna().any():
            date_col = c
            break
    if date_col is None:
        return result
    ts = df[[date_col]].copy()
    ts = ts.dropna(subset=[date_col])
    ts["month"] = ts[date_col].dt.to_period("M").astype(str)
    ts["year"] = ts[date_col].dt.year
    ts["day_of_week"] = ts[date_col].dt.day_name()
    result["by_month"] = ts.groupby("month").size().reset_index(name="ticket_count").sort_values("month").to_dict(orient="records")
    result["by_day_of_week"] = ts.groupby("day_of_week").size().reset_index(name="ticket_count").to_dict(orient="records")
    result["date_range"] = {
        "start": str(ts[date_col].min().date()) if len(ts) else None,
        "end": str(ts[date_col].max().date()) if len(ts) else None,
    }
    return result


def recurring_problems(df: pd.DataFrame, top_n: int = 10) -> dict:
    result = {}
    if "Ticket Subject" in df.columns:
        vc = df["Ticket Subject"].dropna().value_counts().head(top_n)
        result["top_subjects"] = [{"subject": str(k), "count": int(v)} for k, v in vc.items()]
    if "Ticket Type" in df.columns:
        vc2 = df["Ticket Type"].dropna().value_counts().head(top_n)
        result["top_types"] = [{"type": str(k), "count": int(v)} for k, v in vc2.items()]
    if "Ticket Description" in df.columns:
        from collections import Counter
        STOP = set("a an the and or but if then else of to in on for is are was were be been being have has had do does did i you he she it we they them their this that these those with from at by not no my your our as so".split())
        words = Counter()
        for desc in df["Ticket Description"].dropna().astype(str):
            for w in clean_text(desc).lower().split():
                ww = "".join(c for c in w if c.isalpha())
                if len(ww) > 3 and ww not in STOP:
                    words[ww] += 1
        result["top_keywords"] = [{"word": w, "count": c} for w, c in words.most_common(top_n)]
    return result


def business_insights(df: pd.DataFrame, basic_stats: dict, cat_df: pd.DataFrame,
                      pri_df: pd.DataFrame, prod_df: pd.DataFrame,
                      time_info: dict, recurring: dict) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("BUSINESS INSIGHTS REPORT")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("1. MOST COMMON PROBLEM")
    lines.append("-" * 40)
    if recurring.get("top_subjects"):
        ts = recurring["top_subjects"][0]
        lines.append(f"  FACT: Most frequent ticket subject is '{ts['subject']}' with {ts['count']} tickets.")
        total = basic_stats["total_tickets"]
        lines.append(f"  INTERPRETATION: This represents {round(ts['count']/total*100,2)}% of all tickets and may indicate a systemic issue requiring proactive resolution.")
    lines.append("")

    lines.append("2. HIGHEST PRIORITY PROBLEM")
    lines.append("-" * 40)
    if len(pri_df) > 0:
        critical_rows = pri_df[pri_df["Ticket Priority"].astype(str).str.lower() == "critical"]
        if len(critical_rows) > 0:
            r = critical_rows.iloc[0]
            lines.append(f"  FACT: There are {r['ticket_count']} Critical priority tickets. {r['unresolved_count']} ({r['unresolved_pct']}%) remain unresolved.")
            lines.append(f"  INTERPRETATION: Critical unresolved tickets pose operational risk and should be escalated immediately.")
        else:
            highest = pri_df.iloc[0]
            lines.append(f"  FACT: Highest priority tier in data is '{highest['Ticket Priority']}' with {highest['ticket_count']} tickets.")
    lines.append("")

    lines.append("3. PRODUCT WITH HIGHEST TICKET VOLUME")
    lines.append("-" * 40)
    if len(prod_df) > 0:
        top = prod_df.iloc[0]
        lines.append(f"  FACT: Product '{top['Product Purchased']}' generated the most tickets ({top['ticket_count']}).")
        lines.append(f"  INTERPRETATION: This product may benefit from additional support staffing, QA review, or customer-facing documentation.")
    lines.append("")

    lines.append("4. CATEGORY WITH LONGEST RESOLUTION TIME")
    lines.append("-" * 40)
    if len(cat_df) > 0 and cat_df["avg_resolution_hours"].notna().any():
        idx = cat_df["avg_resolution_hours"].idxmax()
        top = cat_df.loc[idx]
        lines.append(f"  FACT: Ticket type '{top['Ticket Type']}' has the longest avg resolution time at {top['avg_resolution_hours']} hours.")
        lines.append(f"  INTERPRETATION: Slow resolution in this category may indicate training gaps, complex tooling, or process bottlenecks.")
    lines.append("")

    lines.append("5. MOST SIGNIFICANT TREND")
    lines.append("-" * 40)
    if time_info.get("by_month") and len(time_info["by_month"]) >= 2:
        months = time_info["by_month"]
        first, last = months[0], months[-1]
        pct = safe_divide((last["ticket_count"] - first["ticket_count"]), first["ticket_count"]) * 100
        direction = "increase" if pct >= 0 else "decrease"
        lines.append(f"  FACT: From {first['month']} to {last['month']}, ticket volume changed by {round(pct,2)}% ({direction}).")
        lines.append(f"  INTERPRETATION: Monitoring this trend helps forecast staffing and support capacity needs.")
    elif time_info.get("date_range"):
        lines.append(f"  FACT: Date range of analyzed timestamps: {time_info['date_range']['start']} to {time_info['date_range']['end']}.")
    lines.append("")

    lines.append("6. UNRESOLVED TICKET PATTERN")
    lines.append("-" * 40)
    lines.append(f"  FACT: {basic_stats['total_unresolved']} of {basic_stats['total_tickets']} tickets are currently unresolved ({round(safe_divide(basic_stats['total_unresolved'], basic_stats['total_tickets'])*100,2)}%).")
    if len(cat_df) > 0:
        top_unres = cat_df.sort_values("unresolved_count", ascending=False).iloc[0]
        lines.append(f"  FACT: Ticket type '{top_unres['Ticket Type']}' has the most unresolved tickets ({top_unres['unresolved_count']}).")
    lines.append(f"  INTERPRETATION: Unresolved tickets affect customer satisfaction and SLA compliance; a backlog review is recommended.")
    lines.append("")

    lines.append("7. POTENTIAL OPERATIONAL IMPROVEMENTS")
    lines.append("-" * 40)
    lines.append("  - Standardize ticket subjects to enable better automated categorization.")
    lines.append("  - Create knowledge-base articles for the top recurring ticket subjects.")
    if basic_stats.get("avg_satisfaction") is not None:
        lines.append(f"  - Current avg satisfaction rating: {basic_stats['avg_satisfaction']}. Investigate segments with below-average scores.")
    lines.append("  - Track First Response Time SLA compliance to reduce initial wait periods.")
    lines.append("")
    return "\n".join(lines)


def save_summary_csvs(
    cat_df: pd.DataFrame, pri_df: pd.DataFrame, status_df: pd.DataFrame,
    prod_df: pd.DataFrame, chan_df: pd.DataFrame
) -> None:
    ensure_dir(config.REPORTS_DIR)
    for name, d in [
        ("category_summary.csv", cat_df),
        ("priority_summary.csv", pri_df),
        ("status_summary.csv", status_df),
        ("product_summary.csv", prod_df),
        ("channel_summary.csv", chan_df),
    ]:
        if d is not None and len(d) > 0:
            d.to_csv(os.path.join(config.REPORTS_DIR, name), index=False)


def run_analysis_pipeline(df: pd.DataFrame) -> dict:
    logger.info("Running analysis pipeline...")
    basic = compute_basic_statistics(df)
    cat_df = category_analysis(df)
    pri_df = priority_analysis(df)
    status_df = status_analysis(df)
    prod_df = product_analysis(df)
    chan_df = channel_analysis(df)
    time_info = time_analysis(df)
    recurring = recurring_problems(df)
    insights = business_insights(df, basic, cat_df, pri_df, prod_df, time_info, recurring)
    write_text_report(config.BUSINESS_INSIGHTS_REPORT, insights)
    save_summary_csvs(cat_df, pri_df, status_df, prod_df, chan_df)
    logger.info(f"Analysis complete. Basic stats: {basic}")
    return {
        "basic": basic,
        "category_df": cat_df,
        "priority_df": pri_df,
        "status_df": status_df,
        "product_df": prod_df,
        "channel_df": chan_df,
        "time_info": time_info,
        "recurring": recurring,
        "business_insights": insights,
    }


def format_basic_stats_text(basic: dict) -> str:
    lines = ["BASIC STATISTICS", "-" * 40]
    for k, v in basic.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)
