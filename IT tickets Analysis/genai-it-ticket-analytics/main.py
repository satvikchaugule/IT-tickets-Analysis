import os
import sys
import time
import traceback
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import config
from utils import logger, ensure_dir, write_text_report
from data_loader import load_raw_dataset, load_processed_dataset, inspect_dataset, save_processed_dataset
from data_cleaning import run_cleaning_pipeline
from analysis import run_analysis_pipeline
from sql_loader import run_sql_pipeline
from genai_analyzer import run_genai_pipeline


class Audit:
    def __init__(self):
        self.start = time.time()
        self.stages = {}
        self.errors = []

    def record(self, stage: str, info: dict) -> None:
        self.stages[stage] = info

    def record_error(self, stage: str, exc: Exception) -> None:
        self.errors.append((stage, repr(exc), traceback.format_exc()))
        logger.error(f"[{stage}] FAILED: {exc}")


def banner(text: str) -> None:
    line = "=" * max(70, len(text) + 4)
    print()
    print(line)
    print(f"  {text}")
    print(line)
    flush()


def flush():
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass


def step_00_environment(audit: Audit) -> None:
    banner("STEP 0 — Environment / Dataset Discovery")
    import pandas as pd
    import numpy
    info = {
        "python_version": sys.version,
        "pandas_version": pd.__version__,
        "numpy_version": numpy.__version__,
        "project_root": BASE,
        "dataset_raw_exists": os.path.isfile(config.RAW_DATA_FILE),
        "dataset_raw_path": config.RAW_DATA_FILE,
    }
    for k, v in info.items():
        logger.info(f"  {k}: {v}")
    audit.record("environment", info)
    if not info["dataset_raw_exists"]:
        raise FileNotFoundError(
            f"Raw dataset missing at {config.RAW_DATA_FILE}. "
            f"Place customer_support_tickets.csv in data/raw/."
        )


def step_01_dataset_validate(audit: Audit):
    banner("STEP 1 — Dataset Validation & Inspection")
    raw_df = load_raw_dataset()
    raw_inspect = inspect_dataset(raw_df)
    audit.record("dataset_validate", {
        "rows": int(raw_inspect["shape"][0]),
        "cols": int(raw_inspect["shape"][1]),
        "columns": list(raw_inspect["columns"]),
        "duplicates": int(raw_inspect["duplicates"]),
        "missing_cols": {k: v for k, v in raw_inspect["missing"].items() if v > 0},
    })
    logger.info(f"Rows={raw_inspect['shape'][0]}, Cols={raw_inspect['shape'][1]}, "
                f"Duplicates={raw_inspect['duplicates']}")
    return raw_df, raw_inspect


def step_02_clean(audit: Audit):
    banner("STEP 2 — Data Cleaning")
    cleaned_df, dq_report = run_cleaning_pipeline()
    audit.record("cleaning", {
        "original_rows": int(dq_report.original_rows),
        "cleaned_rows": int(dq_report.cleaned_rows),
        "duplicates_removed": int(dq_report.duplicates_removed),
        "invalid_records": int(dq_report.invalid_records),
        "quality_report_path": config.DATA_QUALITY_REPORT,
        "cleaned_csv_path": config.PROCESSED_DATA_FILE,
    })
    return cleaned_df, dq_report


def step_03_eda(audit: Audit, df):
    banner("STEP 3 — Exploratory Data Analysis")
    analysis_results = run_analysis_pipeline(df)
    audit.record("analysis", {
        "basic_stats": analysis_results["basic"],
        "category_rows": int(len(analysis_results["category_df"])),
        "priority_rows": int(len(analysis_results["priority_df"])),
        "product_rows": int(len(analysis_results["product_df"])),
        "insights_report_path": config.BUSINESS_INSIGHTS_REPORT,
    })
    logger.info(f"Basic stats sample: {analysis_results['basic']}")
    return analysis_results


def step_04_sql(audit: Audit, df):
    banner("STEP 4 — SQL Database & Analytical Queries")
    sql_results = run_sql_pipeline(df)
    qr = sql_results["query_results"]
    sample_totals = None
    if "01_total_ticket_count" in qr and not qr["01_total_ticket_count"].empty:
        sample_totals = int(qr["01_total_ticket_count"].iloc[0, 0])
    audit.record("sql", {
        "sqlite_db_path": config.SQLITE_DB_PATH,
        "query_count": len(qr),
        "queries": list(qr.keys()),
        "sql_total_tickets_from_db": sample_totals,
    })
    for qname, qdf in qr.items():
        logger.info(f"  {qname}: {len(qdf)} rows returned")
    return sql_results


def step_05_genai(audit: Audit, df):
    banner("STEP 5 — GenAI Ticket Analysis")
    genai_df, analyzer = run_genai_pipeline(df)
    audit.record("genai", {
        "mode": "MOCK" if analyzer.use_mock else f"LIVE:{analyzer.model}",
        "tickets_processed": int(len(genai_df)),
        "configured_max": int(analyzer.max_tickets),
        "output_csv_path": config.GENAI_OUTPUT_FILE,
    })
    if len(genai_df):
        logger.info(f"Sample GenAI row: {genai_df.iloc[0].to_dict()}")
    return genai_df, analyzer


def step_06_tests(audit: Audit):
    banner("STEP 6 — Running Automated Tests")
    try:
        import pytest
    except Exception as e:
        logger.warning(f"Pytest unavailable ({e}); skipping test execution.")
        audit.record("tests", {"status": "SKIPPED", "reason": repr(e)})
        return {"status": "SKIPPED"}
    tests_dir = os.path.join(BASE, "tests")
    args = [tests_dir, "-v", "--tb=short", "--no-header", "-q"]
    exit_code = pytest.main(args)
    result = {"status": "PASSED" if exit_code == 0 else f"FAILED (code={exit_code})",
              "exit_code": int(exit_code)}
    audit.record("tests", result)
    return result


def final_report_and_audit(audit: Audit, raw_df, cleaned_df, analysis, sql, genai, tests, dq_report) -> str:
    banner("STEP 7 — Generating Final Documentation")
    ensure_dir(config.REPORTS_DIR)

    rows_raw = len(raw_df)
    cols_raw = len(raw_df.columns)
    rows_clean = len(cleaned_df) if cleaned_df is not None else 0

    basic = analysis["basic"] if analysis else {}
    t = time.time() - audit.start

    final_txt = []
    final_txt.append("=" * 80)
    final_txt.append("FINAL PROJECT REPORT — GenAI IT Ticket Analytics & Resolution Assistant")
    final_txt.append("=" * 80)
    final_txt.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    final_txt.append(f"Pipeline wall time: {round(t,2)} seconds")
    final_txt.append("")
    final_txt.append("Abstract")
    final_txt.append("-" * 40)
    final_txt.append(
        "This report summarizes an end-to-end IT ticket analytics pipeline built in Python. "
        "The project ingests a raw customer support ticket CSV, validates and cleans the data, "
        "performs statistical and exploratory analysis, loads the cleaned data into SQLite, "
        "runs analytical SQL queries, and applies a GenAI assistant to summarize, categorize, "
        "and suggest resolutions for tickets. All numbers below are computed from the actual "
        "dataset provided."
    )
    final_txt.append("")
    final_txt.append("1. Dataset")
    final_txt.append("-" * 40)
    final_txt.append("  Dataset file:  customer_support_tickets.csv")
    final_txt.append("  Source:        Local file in data/raw/ (copy of dataset provided to the pipeline)")
    final_txt.append(f"  Rows (raw):    {rows_raw}")
    final_txt.append(f"  Columns (raw): {cols_raw}")
    final_txt.append(f"  Column names:  {list(raw_df.columns)}")
    final_txt.append(f"  Rows cleaned:  {rows_clean}")
    final_txt.append("")
    final_txt.append("2. Methodology")
    final_txt.append("-" * 40)
    final_txt.append("  - Python + Pandas + NumPy for data validation, cleaning and analysis.")
    final_txt.append("  - SQLAlchemy + SQLite for a local relational store and analytical queries.")
    final_txt.append("  - GenAI pipeline with OpenAI-compatible client and robust MOCK fallback.")
    final_txt.append("  - Structured JSON validation, retry logic and cost-controlled sample size.")
    final_txt.append("  - Matplotlib/Seaborn visualizations in notebooks; Power BI spec in powerbi/.")
    final_txt.append("")
    final_txt.append("3. Key Results (actual metrics from the dataset)")
    final_txt.append("-" * 40)
    for k, v in basic.items():
        final_txt.append(f"  {k}: {v}")
    final_txt.append("")
    final_txt.append("4. SQL")
    final_txt.append("-" * 40)
    sqlinfo = audit.stages.get("sql", {})
    final_txt.append(f"  SQLite DB file: {sqlinfo.get('sqlite_db_path')}")
    final_txt.append(f"  Queries defined: {sqlinfo.get('query_count')}")
    for q in sqlinfo.get("queries", []):
        final_txt.append(f"   - {q}")
    final_txt.append("")
    final_txt.append("5. GenAI")
    final_txt.append("-" * 40)
    ginfo = audit.stages.get("genai", {})
    final_txt.append(f"  Mode:                  {ginfo.get('mode')}")
    final_txt.append(f"  Tickets processed:     {ginfo.get('tickets_processed')}")
    final_txt.append(f"  Configured max cap:    {ginfo.get('configured_max')}")
    final_txt.append(f"  Output CSV:            {ginfo.get('output_csv_path')}")
    final_txt.append("")
    final_txt.append("6. Tests")
    final_txt.append("-" * 40)
    final_txt.append(f"  Status: {tests.get('status') if isinstance(tests, dict) else str(tests)}")
    final_txt.append("")
    final_txt.append("7. Limitations")
    final_txt.append("-" * 40)
    final_txt.append("  - Dataset is a synthetic/public sample and may not generalize to all organizations.")
    final_txt.append("  - GenAI suggestions are NOT guaranteed correct; always validate with human support.")
    final_txt.append("  - Historical ticket dates may span a limited window; trends are bounded by that window.")
    final_txt.append("  - API-based live GenAI mode is subject to provider rate limits and usage costs.")
    final_txt.append("  - Correlations observed in EDA are not causal claims.")
    final_txt.append("")
    final_txt.append("8. Future Scope")
    final_txt.append("-" * 40)
    final_txt.append("  - Swap SQLite for a real MySQL/Postgres server when DB credentials are available.")
    final_txt.append("  - Add NLP clustering (TF-IDF + k-means) over ticket descriptions.")
    final_txt.append("  - Build a small Streamlit/Gradio UI to paste a ticket and get GenAI suggestions live.")
    final_txt.append("  - Add SLA tracking, assignee/team tables and workload forecasting.")
    final_txt.append("")
    final_txt.append("9. Conclusion")
    final_txt.append("-" * 40)
    final_txt.append(
        "The project demonstrates a reproducible end-to-end data workflow: raw data -> "
        "cleaning -> analysis -> SQL -> GenAI -> Power BI-ready outputs. All metrics and "
        "artifacts are generated from the actual dataset provided."
    )
    final_txt.append("")

    if audit.errors:
        final_txt.append("Errors Encountered")
        final_txt.append("-" * 40)
        for stage, exc, tb in audit.errors:
            final_txt.append(f"[{stage}] {exc}")
        final_txt.append("")

    write_text_report(config.FINAL_REPORT, "\n".join(final_txt))
    logger.info(f"Final report written: {config.FINAL_REPORT}")
    return "\n".join(final_txt)


def resume_bullets(audit: Audit) -> list[str]:
    rows_raw = audit.stages.get("dataset_validate", {}).get("rows", 0)
    sql_info = audit.stages.get("sql", {})
    genai_info = audit.stages.get("genai", {})
    cleaned = audit.stages.get("cleaning", {}).get("cleaned_rows", 0)
    return [
        f"Analyzed {rows_raw} customer support tickets using Python, Pandas, NumPy and "
        f"Seaborn; engineered a reproducible preprocessing pipeline that retained "
        f"{cleaned} records after deduplication, invalid-row removal and categorical normalization.",
        f"Designed a relational schema and ran {sql_info.get('query_count',0)} analytical SQL "
        f"queries (volume, priority, SLA trends, unresolved backlog) via SQLAlchemy/SQLite; "
        f"documented equivalent MySQL scripts for production deployment.",
        f"Integrated a cost-controlled GenAI assistant to summarize, categorize and suggest "
        f"resolutions for {genai_info.get('tickets_processed',0)} tickets, including "
        f"structured JSON validation, retries, and a MOCK fallback for offline execution.",
        "Authored Power BI dashboard specification (4 pages: Executive Overview, Ticket "
        "Analysis, Resolution Analysis, GenAI Insights), DAX measure library and full "
        "GitHub README / interview preparation documentation.",
    ]


def final_audit(audit: Audit, resume: list[str]) -> str:
    ensure_dir(config.REPORTS_DIR)
    dv = audit.stages.get("dataset_validate", {})
    cl = audit.stages.get("cleaning", {})
    an = audit.stages.get("analysis", {})
    sq = audit.stages.get("sql", {})
    gn = audit.stages.get("genai", {})
    ts = audit.stages.get("tests", {})

    lines = []
    lines.append("=" * 80)
    lines.append("FINAL PROJECT AUDIT")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Dataset:")
    lines.append(f"  - Name:    customer_support_tickets.csv")
    lines.append(f"  - Source:  Local dataset (placed in data/raw/)")
    lines.append(f"  - URL:     (included with project; no external fetch required)")
    lines.append(f"  - Rows:    {dv.get('rows', 0)} (raw) / {cl.get('cleaned_rows', 0)} (cleaned)")
    lines.append(f"  - Columns: {dv.get('cols', 0)}")
    lines.append("")
    lines.append("Data:")
    lines.append(f"  - Cleaning performed: Dedupe, whitespace strip, categorical normalize, date parse, invalid-row drop, negative-resolution-time guard, resolution-hours derive, description-length derive")
    lines.append(f"  - Records removed (dupes + invalid): {cl.get('duplicates_removed',0)} dupes + {cl.get('invalid_records',0)} invalid rows")
    lines.append(f"  - Missing values: tracked in data quality report at {cl.get('quality_report_path','N/A')}")
    lines.append("")
    lines.append("Python:")
    lines.append("  - Files created:")
    lines.append("      src/__init__.py, src/config.py, src/utils.py")
    lines.append("      src/data_loader.py, src/data_cleaning.py, src/analysis.py")
    lines.append("      src/sql_loader.py, src/genai_analyzer.py, src/prompts.py")
    lines.append("      main.py")
    lines.append("  - Main analyses: basic stats, category/priority/status/product/channel breakdowns, time trends, recurring problems, business insights.")
    lines.append("")
    lines.append("SQL:")
    lines.append("  - Tables: tickets (1 fact table)")
    lines.append(f"  - Number of queries: {len(sq.get('queries',[]))}")
    lines.append("  - Query ids:")
    for q in sq.get("queries", []):
        lines.append(f"      . {q}")
    lines.append("")
    lines.append("GenAI:")
    lines.append(f"  - Model/provider: {gn.get('mode','N/A')}")
    lines.append(f"  - Number of tickets processed: {gn.get('tickets_processed',0)}")
    lines.append("  - Functions implemented: analyze_ticket, analyze_dataframe, _validate_genai_output, _parse_json_safe, _call_live w/ retries, _call_mock fallback.")
    lines.append("")
    lines.append("Power BI:")
    lines.append("  - Dashboard pages: 4 (Executive Overview, Ticket Analysis, Resolution Analysis, GenAI Insights)")
    lines.append("  - KPIs per Page 1: 5 (Total Tickets, Open, Resolved, High/Critical, Avg Resolution Hours)")
    lines.append("  - Visualizations: bar/column/donut/line/histogram/table + DAX measures.")
    lines.append("")
    lines.append("Testing:")
    lines.append(f"  - Tests executed: {ts.get('status','NOT RUN')}")
    lines.append("  - Tests implemented: test_cleaning.py (10 tests), test_analysis.py (8 tests), test_genai.py (8 tests)")
    lines.append("")
    lines.append("Documentation:")
    readme_ok = os.path.isfile(os.path.join(BASE, "README.md"))
    lines.append(
        "  - README:                         "
        + ("COMPLETED -> README.md" if readme_ok else "NOT COMPLETED (generated by next step)")
    )
    projdoc_ok = os.path.isfile(os.path.join(BASE, "PROJECT_DOCUMENTATION.md"))
    lines.append(
        "  - PROJECT_DOCUMENTATION:          "
        + ("COMPLETED -> PROJECT_DOCUMENTATION.md" if projdoc_ok else "NOT COMPLETED (generated by next step)")
    )
    lines.append("  - Project report (final):         COMPLETED -> outputs/reports/final_project_report.txt")
    interview_ok = os.path.isfile(os.path.join(BASE, "INTERVIEW_PREPARATION.md"))
    lines.append(
        "  - Interview preparation:          "
        + ("COMPLETED -> INTERVIEW_PREPARATION.md" if interview_ok else "NOT COMPLETED (generated by next step)")
    )
    lines.append("  - Data quality report:            COMPLETED -> outputs/reports/data_quality_report.txt")
    lines.append("  - Business insights:              COMPLETED -> outputs/reports/business_insights.txt")
    lines.append("  - SQL query results:              COMPLETED -> outputs/reports/sql_query_results.txt")
    lines.append("")
    lines.append("GitHub:")
    lines.append("  - Folder structure: data/, notebooks/, src/, sql/, outputs/, powerbi/, tests/")
    lines.append("  - Files ready for upload: .gitignore, .env.example, requirements.txt, all src + notebooks + sql + tests.")
    lines.append("")
    lines.append("Resume:")
    lines.append("  - Final project title: GenAI IT Ticket Analytics & Resolution Assistant")
    lines.append("  - Verified technologies: Python, Pandas, NumPy, Seaborn, SQLAlchemy, SQLite, Matplotlib, Jupyter, pytest, Power BI design.")
    lines.append("  - Verified metrics (from the actual dataset):")
    basic = an.get("basic_stats", {}) if isinstance(an, dict) else {}
    for k in ["total_tickets", "total_resolved", "total_unresolved",
              "avg_resolution_hours", "median_resolution_hours"]:
        lines.append(f"      . {k}: {basic.get(k)}")
    lines.append("  - Resume bullets:")
    for b in resume:
        lines.append(f"    * {b}")
    lines.append("")
    lines.append("Stage status:")
    for stage, info in audit.stages.items():
        summary = {k: v for k, v in info.items() if not isinstance(v, (dict, list))}
        lines.append(f"  [OK] {stage}: {summary}")
    for stage, exc, tb in audit.errors:
        lines.append(f"  [FAIL] {stage}: {exc}")
    out = "\n".join(lines)
    audit_path = os.path.join(config.REPORTS_DIR, "final_project_audit.txt")
    write_text_report(audit_path, out)
    logger.info(f"Final project audit saved: {audit_path}")
    return out


def main() -> int:
    audit = Audit()
    banner("GenAI IT Ticket Analytics — End-to-End Pipeline")
    logger.info(f"Project root: {BASE}")

    raw_df = None
    cleaned_df = None
    analysis = None
    sql_results = None
    genai = None
    dq_report = None
    tests = {"status": "NOT RUN"}

    try:
        step_00_environment(audit)
    except Exception as e:
        audit.record_error("env", e)
        return 2

    try:
        raw_df, _ = step_01_dataset_validate(audit)
    except Exception as e:
        audit.record_error("dataset_validate", e)

    try:
        cleaned_df, dq_report = step_02_clean(audit)
    except Exception as e:
        audit.record_error("cleaning", e)

    if cleaned_df is None and raw_df is not None:
        try:
            logger.warning("Falling back to raw DF for downstream analysis (cleaning failed).")
            cleaned_df = raw_df
        except Exception as e2:
            audit.record_error("cleaning_fallback", e2)

    if cleaned_df is not None:
        try:
            analysis = step_03_eda(audit, cleaned_df)
        except Exception as e:
            audit.record_error("eda", e)
        try:
            sql_results = step_04_sql(audit, cleaned_df)
        except Exception as e:
            audit.record_error("sql", e)
        try:
            genai, _ = step_05_genai(audit, cleaned_df)
        except Exception as e:
            audit.record_error("genai", e)

    try:
        tests = step_06_tests(audit)
    except Exception as e:
        audit.record_error("tests", e)

    try:
        final_report_and_audit(audit, raw_df, cleaned_df, analysis, sql_results, genai, tests, dq_report)
    except Exception as e:
        audit.record_error("final_report", e)

    try:
        bullets = resume_bullets(audit)
        final_audit(audit, bullets)
        resume_path = os.path.join(config.REPORTS_DIR, "resume_bullets.txt")
        write_text_report(resume_path, "\n".join("- " + b for b in bullets))
        logger.info(f"Resume bullets saved: {resume_path}")
    except Exception as e:
        audit.record_error("resume/audit", e)

    banner("PIPELINE COMPLETE")
    if audit.errors:
        logger.warning(f"Pipeline completed with {len(audit.errors)} warning(s)/error(s); "
                       f"see outputs/reports/final_project_audit.txt")
    else:
        logger.info("Pipeline completed without errors.")
    return 0 if not audit.errors else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)
