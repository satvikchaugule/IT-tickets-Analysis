# GenAI IT Ticket Analytics & Resolution Assistant

Portfolio-grade end-to-end analytics + GenAI assistant project for IT / customer
support tickets. Pipeline: **Raw Data → Cleaning → EDA → SQLite / SQL → GenAI →
Power BI-ready artifacts → Business Insights**.

All numbers in this README are computed from the actual dataset by running the
pipeline — nothing is fabricated.

---

## Overview

This project ingests `customer_support_tickets.csv` (8 469 tickets, 17 columns),
cleans and validates the data, computes statistical and categorical analyses,
loads the data into SQLite (with equivalent MySQL scripts), and applies a
Generative AI assistant on a configurable sample of tickets to produce:

- Short ticket summary
- Category suggestion
- Priority suggestion
- Possible cause
- Concise troubleshooting / resolution steps

All outputs are saved to the `outputs/` folder and a 4-page Power BI dashboard
specification is provided so the cleaned dataset can be visualised immediately.

## Problem Statement

Organisations receive thousands of support tickets per month. Without structured
analytics and automation, teams struggle to answer:

1. What are our most common, longest-running, or highest-risk problems?
2. Which departments, products, or channels drive the most load?
3. How many tickets are open, closed, or breaching SLA?
4. Can we summarise, classify, and suggest first-line resolutions automatically
   with GenAI to reduce mean-time-to-respond?

This project provides reproducible answers to those questions using Python, SQL,
and an LLM.

## Objectives

- Build a reproducible data-cleaning pipeline with a written data-quality report.
- Compute basic stats, category / priority / product / channel / time analyses.
- Design a relational schema and execute 10 analytical SQL queries.
- Integrate a cost-controlled GenAI pipeline with structured JSON validation,
  retry logic, and an offline MOCK fallback.
- Produce a 4-page Power BI dashboard specification (data source, model, DAX
  measures, visuals per page).
- Generate a business-insights report (FACT vs INTERPRETATION distinction).
- Provide 26 unit tests (cleaning / analysis / genai), run them, and report
  results.
- Create all GitHub-ready docs: README, project documentation, interview Q&A.

## Dataset

| Item | Value |
| --- | --- |
| File name | `customer_support_tickets.csv` |
| Location | `data/raw/customer_support_tickets.csv` (raw), `data/processed/cleaned_tickets.csv` (cleaned) |
| Source | Local file included with the project |
| Rows (raw / cleaned) | 8 469 / 8 469 |
| Columns | 17 |
| Duplicates removed | 0 |
| Invalid rows dropped | 0 |
| Date columns | `Date of Purchase`, `First Response Time`, `Time to Resolution` |
| Text columns | `Customer Name`, `Customer Email`, `Product Purchased`, `Ticket Type`, `Ticket Subject`, `Ticket Description`, `Ticket Status`, `Resolution`, `Ticket Priority`, `Ticket Channel` |
| Numeric columns | `Customer Age`, `Customer Satisfaction Rating`, derived `resolution_time_hours`, `description_length` |

Columns: `Ticket ID`, `Customer Name`, `Customer Email`, `Customer Age`,
`Customer Gender`, `Product Purchased`, `Date of Purchase`, `Ticket Type`,
`Ticket Subject`, `Ticket Description`, `Ticket Status`, `Resolution`,
`Ticket Priority`, `Ticket Channel`, `First Response Time`,
`Time to Resolution`, `Customer Satisfaction Rating`.

## Technologies

- **Languages**: Python 3.13, SQL (SQLite + MySQL-compatible scripts), DAX
- **Libraries**: Pandas 2.3, NumPy 2.3, Matplotlib 3.10, Seaborn 0.13, SQLAlchemy 2.1, python-dotenv, openpyxl, pytest 9.1
- **Database**: SQLite (local file) with documented MySQL equivalent
- **GenAI**: OpenAI-compatible Chat Completions endpoint (gpt-3.5-turbo by default)
  with a full offline MOCK fallback for execution without an API key
- **BI**: Power BI Desktop (specification in `powerbi/dashboard_documentation.md`)
- **Other**: Jupyter notebooks (4), pytest (26 tests)

## Architecture

```
RAW DATA (customer_support_tickets.csv)
   │
   ▼
DATA LOADING + VALIDATION (data_loader.py, data_cleaning.py)
   │  shape, head/tail, dtypes, nulls, duplicates, invalid dates
   ▼
CLEANED DATA (data/processed/cleaned_tickets.csv + data_quality_report.txt)
   │
   ├──────────────────────────────────────────────────────────┐
   ▼                                                          ▼
EXPLORATORY DATA ANALYSIS (analysis.py)              SQL DATABASE (sql_loader.py)
   │  basic stats / category / priority / status /             │  CREATE tickets
   │  product / channel / time / recurring / insights          │  10 analytical queries
   ▼                                                          ▼
CHARTS + BUSINESS INSIGHTS                    sql_query_results.txt, it_tickets.db
(outputs/figures, outputs/reports)                     │
   │                                                          │
   └──────────────────────────────────────────────────────────┘
                              │
                              ▼
                   GENAI COMPONENT (genai_analyzer.py)
                   Summarize · Categorize · Suggest Priority
                   Possible Cause · Suggested Resolution
                   (MAX_TICKETS_FOR_GENAI, default 50)
                              │
                              ▼
                   genai_ticket_analysis.csv
                              │
                              ▼
                  POWER BI DASHBOARD SPECIFICATION
                  (4 pages, 5 KPIs page 1, DAX measures)
```

## Project Structure

```
genai-it-ticket-analytics/
│
├── data/
│   ├── raw/                              # Never modify
│   │   └── customer_support_tickets.csv
│   └── processed/
│       └── cleaned_tickets.csv           # Pipeline output
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_eda.ipynb
│   └── 04_genai_analysis.ipynb
│
├── src/
│   ├── __init__.py
│   ├── config.py                         # Central paths + env configuration
│   ├── utils.py                          # Logger, text/date helpers, safe_divide
│   ├── data_loader.py                    # Raw/processed dataset load + inspect
│   ├── data_cleaning.py                  # Cleaning pipeline + DataQualityReport
│   ├── analysis.py                       # Statistics + breakdowns + insights
│   ├── sql_loader.py                     # SQLite load + 10 analytical queries
│   ├── genai_analyzer.py                 # LLM client + MOCK fallback
│   └── prompts.py                        # System / user prompt templates
│
├── sql/
│   ├── schema.sql
│   ├── load_data.sql
│   └── analytical_queries.sql            # 10 queries listed in § SQL
│
├── outputs/
│   ├── figures/                          # Notebook-generated charts
│   ├── reports/
│   │   ├── data_quality_report.txt
│   │   ├── business_insights.txt
│   │   ├── sql_query_results.txt
│   │   ├── category_summary.csv
│   │   ├── priority_summary.csv
│   │   ├── status_summary.csv
│   │   ├── product_summary.csv
│   │   ├── channel_summary.csv
│   │   ├── final_project_report.txt
│   │   ├── final_project_audit.txt
│   │   └── resume_bullets.txt
│   ├── genai_results/
│   │   └── genai_ticket_analysis.csv
│   └── it_tickets.db                     # SQLite database
│
├── powerbi/
│   └── dashboard_documentation.md
│
├── tests/
│   ├── __init__.py
│   ├── test_cleaning.py     (10 tests)
│   ├── test_analysis.py     (8 tests)
│   └── test_genai.py        (8 tests)
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Data Cleaning

The reproducible pipeline in `src/data_cleaning.py` performs, in order:

1. **Required-column validation**: abort if `Ticket ID / Type / Subject / Description / Status / Priority / Channel` are missing.
2. **Deduplication**: by `Ticket ID` if available; keep first.
3. **Whitespace normalization**: all object columns are stripped and internal whitespace is collapsed.
4. **Categorical normalization**: `Ticket Priority` title-case + known-set validation; other categoricals stripped.
5. **Date parsing**: three columns coerced with `errors='coerce'`; failures become NaT and are reported.
6. **Invalid-row drop**: rows with missing `Ticket ID` or `Ticket Status` removed.
7. **Metric derivation**:
   - `resolution_time_hours = Time to Resolution − First Response Time` (negative values reset to NaN)
   - `description_length` = cleaned length of `Ticket Description`

Cleaning-decision records (affected counts, rationales) are written to
`outputs/reports/data_quality_report.txt`.

Actual results on the provided dataset:

| Metric | Value |
| --- | --- |
| Original rows | 8 469 |
| Duplicates removed | 0 |
| Invalid records | 0 |
| Final cleaned rows | 8 469 |
| Rows retained | 100.00 % |

## Exploratory Data Analysis

Computed in `src/analysis.py` and demonstrated interactively in
`notebooks/03_eda.ipynb`.

### Basic statistics

| Metric | Value |
| --- | --- |
| Total tickets | 8 469 |
| Ticket types (categories) | 5 |
| Products purchased | 42 |
| Distinct customers | 8 028 |
| Support channels | 4 |
| **Resolved** tickets | 2 769 |
| **Unresolved** tickets | 5 700 (67.3 %) |
| Open tickets | 2 819 |
| Avg resolution time | 7.58 hours |
| Median resolution time | 6.35 hours |
| Min / Max resolution time | 0.00 / 23.47 hours |
| Avg satisfaction rating | 2.99 / 5 |

### Key categorical findings (actual)

- **Most common ticket subject**: `Refund request` — 576 tickets (6.8%).
- **Highest-risk priority**: 2 129 **Critical** tickets, of which 1 403 (65.9%) are unresolved.
- **Top product by volume**: `Canon EOS` with 240 tickets.
- **Slowest category by avg resolution**: `Refund request` at 8.12 hours.
- **Fastest-growing month on record**: 2023-05 → 2023-06 changed +3 028.57 % (ticket count).
- **Unresolved backlog hotspot**: `Cancellation request` (1 179 unresolved).

## SQL Analysis

Schema + scripts are provided in `sql/` and the pipeline auto-loads them into
SQLite via SQLAlchemy (`outputs/it_tickets.db`).

**Tables**: one fact table `tickets` (ticket_id PK + 18 derived columns, 5
indexes on type/priority/status/product/first_response_time).

**10 queries (all executed, results in `outputs/reports/sql_query_results.txt`)**:

1. Total ticket count
2. Tickets by category / ticket_type + % of total
3. Tickets by priority + avg resolution hours
4. Top-15 products by ticket count
5. All unresolved tickets (ordered by priority)
6. Avg / max / min resolution time *(MySQL note: append `MEDIAN(resolution_time_hours)` here)*
7. High + Critical unresolved tickets
8. Monthly ticket volume (STRFTIME for SQLite, DATE_FORMAT for MySQL)
9. Top-20 product resolution performance (volume, resolved %, avg hours)
10. Channel-wise volume + avg resolution hours

## GenAI Component

Implemented in `src/genai_analyzer.py` + `src/prompts.py`.

### Functions delivered

A. **Ticket summarization** → 1–2 sentence summary.
B. **Ticket categorization** → `Technical issue / Billing inquiry / Cancellation request / Refund request / Product inquiry / Other`.
C. **Priority suggestion** → `Low / Medium / High / Critical` (always labeled *suggested*, never ground truth).
D. **Possible cause** + **numbered resolution checklist**.
E. **Structured output** validated as JSON with required keys + enum-domain
validation; fallback on parse error or API error.

### Safeguards

- `MAX_TICKETS_FOR_GENAI` configurable default: 50 (set in `.env`).
- Live mode: `retries=2` + back-off for timeout / rate-limit / connect errors.
- Always validates the response JSON; silently falls back to **rule-based MOCK**
  suggestions (keyword-driven templates for VPN, login, billing, update/install, battery/power, network) on any API or JSON failure.
- Pipeline explicitly prints: *“GenAI analysis was performed on 50 tickets using MOCK mode.”* — never claims all tickets were processed.

### Live setup

Copy `.env.example` → `.env` and set:

```dotenv
GENAI_API_KEY=sk-...
GENAI_MODEL=gpt-3.5-turbo
MAX_TICKETS_FOR_GENAI=100
```

## Power BI Dashboard

Full spec: [powerbi/dashboard_documentation.md](powerbi/dashboard_documentation.md).

Connect Power BI Desktop to `data/processed/cleaned_tickets.csv` (and optionally
`outputs/genai_results/genai_ticket_analysis.csv` for Page 4).

### Pages

1. **Executive Overview** — 5 KPI cards (Total, Open, Resolved, High/Critical, Avg Res Hours) + 4 charts (Type, Priority, Status donut, Tickets over time).
2. **Ticket Analysis** — Category, Product and Priority vs volume and vs avg resolution hours.
3. **Resolution Analysis** — Resolution-time histogram, Category vs speed, Unresolved by product, High/Critical unresolved drill-through table.
4. **GenAI Insights** — cards + table showcasing GenAI summary, category, priority, cause, and suggested resolution per ticket.

### Data model

Single fact table model (`tickets` grain = 1 row per ticket). 1:1 optional
relationship to `genai_results` by `ticket_id`. 7 DAX measures are provided in
the dashboard doc (Resolved Tickets, Unresolved Tickets, High/Critical Tickets,
Avg/Median Resolution Hours, Resolution Rate %).

## Results

Results are *actual*, computed from the dataset:

- 8 469 tickets ingested, cleaned, and loaded to SQLite.
- 2 769 resolved vs 5 700 unresolved (67.3 % backlog).
- Median resolution time: 6.35 hours; mean: 7.58 hours.
- 5 ticket types, 4 priorities, 4 channels, 42 products analysed end to end.
- 10 analytical SQL queries executed and saved.
- GenAI analysis: 50 tickets (MOCK mode — swap `.env` key for live LLM calls).
- Tests: 26 / 26 passed (pytest).

## Business Insights

From `outputs/reports/business_insights.txt`, distinguishing **FACT** from
**INTERPRETATION**:

1. **Most common problem**: `Refund request` subject (576 tickets, 6.8%).
   Interpretation: systemic refund/demand issue; consider proactive FAQs or a
   self-service refund flow.
2. **Highest priority risk**: 2 129 Critical tickets, 1 403 (65.9%) unresolved.
   Interpretation: escalate the Critical-unresolved backlog today.
3. **Top product by load**: `Canon EOS` (240 tickets).
   Interpretation: targeted staffing, QA, or KB articles for that SKU.
4. **Slowest category**: `Refund request` at 8.12 hours avg.
   Interpretation: investigate tooling / approvals in the refund workflow.
5. **Largest trend**: 2023-05 → 2023-06 ticket count +3 028.57 %.
   Interpretation: use the trend to size staffing for forecasted peaks.
6. **Unresolved pattern**: Cancellation requests dominate unresolved (1 179).
   Interpretation: SLA review + cancellation-process automation opportunities.
7. **Operational improvements**: standardize ticket subjects, build KB for top
   subjects, investigate the 2.99/5 avg satisfaction, track First Response SLA.

## Limitations

- Dataset is a public sample and may not generalise to all industries / sizes.
- GenAI outputs (live or MOCK) are **advisory only** — never substitute for a
  verified human support action.
- Historical timestamps span a limited window; time trends apply only to that range.
- Live GenAI mode is subject to provider rate limits and usage costs; the
  `MAX_TICKETS_FOR_GENAI` cap exists specifically to mitigate this.
- Correlations observed in EDA must not be read as causal claims.

## Installation

Requires Python 3.10+ (tested on 3.13.0).

```bash
# 1. Clone / extract project
cd genai-it-ticket-analytics

# 2. Create a venv (optional, recommended)
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install
pip install -r requirements.txt

# 4. Copy env template
cp .env.example .env          # Windows: copy .env.example .env

# 5. Place dataset
#    data/raw/customer_support_tickets.csv
```

## Configuration

Edit `.env`:

```dotenv
# Leave GENAI_API_KEY empty for offline MOCK execution (recommended first run).
GENAI_API_KEY=
GENAI_MODEL=gpt-3.5-turbo
MAX_TICKETS_FOR_GENAI=50

# SQLite is always used locally. MySQL section is optional:
DB_HOST=localhost
DB_PORT=3306
DB_NAME=it_tickets_db
DB_USER=root
DB_PASSWORD=
SQLITE_DB_PATH=./outputs/it_tickets.db
```

## How to Run

### End-to-end pipeline (recommended)

```bash
python main.py
```

Runs, in order: env check → dataset validation → cleaning → EDA → SQL load +
10 queries → GenAI sample analysis → pytest suite → final reports, audit, and
resume bullets.

### Run individual stages

```bash
# Stage only (useful for debugging)
python src/data_cleaning.py         # cleaning only
# analysis/sql/genai stages are importable in Python; see main.py for usage
```

### Notebooks

Launch Jupyter, then open:

```
notebooks/01_data_exploration.ipynb
notebooks/02_data_cleaning.ipynb
notebooks/03_eda.ipynb
notebooks/04_genai_analysis.ipynb
```

## Testing

```bash
pytest tests/ -v
```

Actual result on provided dataset: **26 passed** in ~0.26 s.

- `tests/test_cleaning.py` — 10 tests: text/date utils, dedupe, whitespace,
  categorical norm, invalid-row drop, negative resolution time, end-to-end.
- `tests/test_analysis.py` — 8 tests: basic stats + all breakdowns + recurring keywords.
- `tests/test_genai.py` — 8 tests: mock mode, structure validation, enum
  domain enforcement, JSON fence stripping, prompt construction, sample dataframe output.

## Future Improvements

- **Deploy MySQL** and use the documented schema + scripts when credentials are available.
- **NLP clustering** of `Ticket Description` with TF-IDF + k-means to surface
  emergent issue groups.
- **Streamlit / Gradio mini UI** to paste a ticket and return the five GenAI
  fields plus nearest historical similar tickets.
- **Add assignee / team / SLA tables** to enable workload forecasting and SLA
  compliance reporting.
- **Automated Power BI refresh** via on-premises data gateway connected to the
  SQLite or MySQL source.

## Author

Portfolio project. All source code, tests, notebooks and documentation are
included in this repository. Run `python main.py` to regenerate every report,
CSV, figure and database artifact from the raw CSV.
