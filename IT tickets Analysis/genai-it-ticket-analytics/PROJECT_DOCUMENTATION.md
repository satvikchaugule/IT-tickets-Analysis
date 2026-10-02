# PROJECT DOCUMENTATION

## 1. Problem Statement

Organisations that operate customer support or IT helpdesks face three recurring
operational pains that are classic data-science targets:

1. **Unstructured backlog visibility**: raw tickets sit in a CSV / tool
   export with no structured breakdown of category, priority, product, or
   channel — so managers cannot size, triage, or staff correctly.
2. **Slow first response**: every new ticket is manually read, triaged, and
   assigned, creating a serial bottleneck that pushes up first-response time
   and lowers CSAT.
3. **Knowledge repetition**: frequently seen issues (login / VPN failures,
   billing disputes, install / update blockers, product setup) are solved with
   nearly the same troubleshooting steps every single time, yet the team does
   not surface those resolutions automatically.

A reproducible analytics + GenAI pipeline resolves all three.

## 2. Motivation

This portfolio project was built to demonstrate a student-endorsed,
production-shape workflow: **raw CSV → cleaning (with audit log) → EDA →
SQL-analytics → GenAI summarisation + categorisation + resolution assistant →
Power BI dashboard design → unit-tested, documented, git-ready deliverables**.

The specific dataset chosen (`customer_support_tickets.csv`) is realistic:
mixed categorical / date / numeric fields, significant unresolved backlog,
sparse CSAT, and free-form ticket text. It contains enough rows (8 469) and
enough cardinality (42 products, 5 types, 4 channels) to produce non-trivial
analytics.

## 3. Dataset Description

### 3.1 Provenance

- File name: `customer_support_tickets.csv`
- Location in project: `data/raw/customer_support_tickets.csv`
- Delivered with: the project itself (no external network fetch)

### 3.2 Schema (17 raw columns)

| # | Name | Dtype (raw) | Purpose |
| - | - | - | - |
| 1 | Ticket ID | int | PK |
| 2 | Customer Name | str | Contact identifier |
| 3 | Customer Email | str | Contact identifier |
| 4 | Customer Age | int | Demographic |
| 5 | Customer Gender | str | Demographic |
| 6 | Product Purchased | str | SKU dimension |
| 7 | Date of Purchase | datetime | Timeline anchor |
| 8 | Ticket Type | enum-like | Category (5 values) |
| 9 | Ticket Subject | str | Short title / topic |
| 10 | Ticket Description | str | Free-form narrative |
| 11 | Ticket Status | enum-like | Open / Closed / Resolved / … |
| 12 | Resolution | str | Post-resolution text |
| 13 | Ticket Priority | enum-like | Low / Medium / High / Critical |
| 14 | Ticket Channel | enum-like | 4 channels |
| 15 | First Response Time | datetime | SLA start |
| 16 | Time to Resolution | datetime | SLA end |
| 17 | Customer Satisfaction Rating | float (nullable) | 1–5 CSAT |

### 3.3 Scale (actual figures)

- Raw rows: 8 469
- Clean rows (post dedupe + invalid-drop + guardrails): 8 469
- Rows retained: 100.00 %
- Distinct customers: 8 028
- Distinct products: 42
- Priority cardinality: 4
- Channel cardinality: 4
- Ticket type cardinality: 5

## 4. Data Preprocessing / Cleaning Pipeline

Implemented in `src/data_cleaning.py`. Pipeline is reproducible: identical
raw CSV + same code → byte-stable `cleaned_tickets.csv`.

### 4.1 Order of operations

1. **Required-column guard**: missing any one of
   `{Ticket ID, Type, Subject, Description, Status, Priority, Channel}` →
   abort with a `ValueError`.
2. **Deduplication**: keep-first by `Ticket ID`.
3. **Whitespace normalisation**: `str.strip()` + collapse internal runs of
   whitespace for every object column.
4. **Priority canonicalisation**: `.title().strip()`; values outside
   `{Low, Medium, High, Critical}` forced to `"Unclassified"`.
5. **Date coercion**: `pd.to_datetime(..., errors='coerce')` on
   Date-of-Purchase / First-Response / Time-to-Resolution; failed parses
   counted and reported.
6. **Invalid-row drop**: missing Ticket ID or missing Ticket Status → removed;
   count reported.
7. **Derivations**:
   - `resolution_time_hours` = (Time_to_Resolution − First_Response_Time)
     in hours. Negative values guard-railed to `NaN` with count.
   - `description_length` = `len(clean_text(ticket_description))`.

### 4.2 Data Quality Report (actual)

Saved to `outputs/reports/data_quality_report.txt`:

- Before / after missing-value tables per column.
- Cleaning decisions log with affected row counts.
- Final schema + sample rows.
- Duplicates: 0 removed.
- Invalid records: 0 removed.
- Negative resolution-time guard: 0 rows reset.

## 5. Exploratory Data Analysis

Produced by `src/analysis.py::run_analysis_pipeline`; interactively shown in
`notebooks/03_eda.ipynb`.

### 5.1 Basic statistics (actual figures)

| KPI | Value |
| - | - |
| Total tickets | 8 469 |
| Ticket types | 5 |
| Products | 42 |
| Distinct customers | 8 028 |
| Channels | 4 |
| Resolved | 2 769 |
| Unresolved | 5 700 (67.3 %) |
| Open | 2 819 |
| Avg resolution time | 7.58 hours |
| Median resolution time | 6.35 hours |
| Min / Max resolution time | 0.00 / 23.47 hours |
| Avg satisfaction rating | 2.99 / 5 |

### 5.2 Category / priority / product / channel / time

Each breakdown is saved as a CSV (`category_summary.csv`, `priority_summary.csv`,
`status_summary.csv`, `product_summary.csv`, `channel_summary.csv`) and used
directly by Pages 1–3 of the Power BI specification.

Headline categorical takeaways (actual figures):

- Subjects: `Refund request` #1 at 576 / 6.8 %.
- Critical: 2 129 total, 1 403 unresolved (65.9 %).
- Product: `Canon EOS` #1 at 240 tickets.
- Slowest: `Refund request` avg = 8.12 hours.
- Largest monthly delta: 2023-05 → 2023-06 (+3 028.57 %).
- Unresolved hotspot: `Cancellation request` 1 179.

### 5.3 Distribution / trend visuals

Recommended Seaborn charts (already plotted in `03_eda.ipynb`):

- Count plot: tickets by Type, Priority, Channel.
- Histogram + KDE: resolution_time_hours.
- Line chart: tickets per month.
- Heatmap-like product × priority cross-tab.
- Bar: top-15 products; top-15 subjects.

## 6. SQL Analysis

### 6.1 Schema design

Single star fact table. `sql/schema.sql` (SQLite) creates:

```
tickets (
    ticket_id          INTEGER PRIMARY KEY,
    customer_name      TEXT, customer_email      TEXT,
    customer_age       INTEGER, customer_gender   TEXT,
    product_purchased  TEXT, date_of_purchase    TIMESTAMP,
    ticket_type        TEXT, ticket_subject      TEXT,
    ticket_description TEXT, ticket_status       TEXT,
    resolution         TEXT, ticket_priority     TEXT,
    ticket_channel     TEXT,
    first_response_time        TIMESTAMP,
    time_to_resolution         TIMESTAMP,
    customer_satisfaction_rating REAL,
    resolution_time_hours      REAL,
    description_length         INTEGER
)
+ 5 secondary indexes on (type, priority, status, product, first_response_time).
```

MySQL-equivalent schema is documented inline (replace `INTEGER PRIMARY KEY`
→ `INT AUTO_INCREMENT PRIMARY KEY`, `TEXT` → `VARCHAR(...)`, `TIMESTAMP`
→ `DATETIME`).

### 6.2 Data load

Pipeline uses `pandas.DataFrame.to_sql(..., if_exists='replace', index=False)`
through SQLAlchemy. Load output on actual run: 8 469 rows inserted in ~4 s.

MySQL reference (documented in `sql/load_data.sql`):
`LOAD DATA INFILE ... INTO TABLE tickets FIELDS TERMINATED BY ',' ... IGNORE 1 LINES;`

### 6.3 10 analytical queries (all executed)

Results in `outputs/reports/sql_query_results.txt`.

| # | Name | Outputs |
| - | - | - |
| 01 | Total ticket count | scalar (8 469) |
| 02 | Tickets by category | 5 rows: count, % of total |
| 03 | Tickets by priority | 4 rows: count + avg res hrs |
| 04 | Tickets by product (top 15) | 15 rows |
| 05 | Unresolved tickets | 5 700 rows, priority-ordered |
| 06 | Avg / max / min resolution time | 1 row (MySQL can append MEDIAN) |
| 07 | High + Critical unresolved | 2 783 rows |
| 08 | Monthly ticket volume | 2 rows |
| 09 | Product resolution performance (top 20) | 20 rows (resolved %, avg hrs) |
| 10 | Channel performance | 4 rows |

Portability note: Query 06 uses `AVG / MAX / MIN` (works on both SQLite and
MySQL). MySQL users can additionally append `ROUND(MEDIAN(resolution_time_hours), 2)
AS median_resolution_hours` (documented as a comment). Query 08 uses
`STRFTIME('%Y-%m', …)` for SQLite and `DATE_FORMAT(…, '%Y-%m')` for MySQL
documented inline.

## 7. Generative AI (GenAI) Component

### 7.1 Responsibilities

The `GenAIAnalyzer` class in `src/genai_analyzer.py` produces, per ticket, a
strict JSON object with keys:

| Key | Type / Domain | Purpose |
| - | - | - |
| summary | str (1–2 sentences) | Human-readable short summary |
| category | enum: Technical issue / Billing inquiry / Cancellation request / Refund request / Product inquiry / Other | Automated classification |
| suggested_priority | enum: Low / Medium / High / Critical | Advisory only |
| possible_cause | str paragraph | Likely root cause |
| suggested_resolution | str, numbered checklist 1..N | First-line steps |

Prompt templates live in `src/prompts.py`: system prompt defines JSON schema +
enum-domain contract; per-ticket user prompt injects
`(Ticket ID, Type, Subject, Description, Priority, Channel, Product)`.

### 7.2 Architecture

```
analyze_ticket(ticket_row)
│
├─ _init_client()
│    ├─ if GENAI_API_KEY set → openai.OpenAI(timeout=30s)
│    └─ else                 → MOCK branch
│
├─ _call_live()          [live path]
│    ├─ 2 retries, exponential backoff
│    ├─ catches: timeout, rate limit (429), APIError, any Exception
│    └─ falls back to _call_mock() if any call fails
│
├─ _call_mock()          [mock path, keyword-driven]
│    ├─ rules for: vpn/login, billing, update/install, battery/power, network
│    └─ generic fallback for unrecognised tickets
│
├─ _parse_json_safe()        strips ``` fences, finds first JSON object
├─ _validate_genai_output()  required keys present + enums in allowed set
└─ returns dict with an extra '_genai_status': 'ok' | 'mock'
```

### 7.3 Cost controls

- `MAX_TICKETS_FOR_GENAI` env var (default 50).
- Only the first `MAX_TICKETS_FOR_GENAI` rows (ordered by Ticket ID) are
  processed; a logging line prints `N/TOTAL` actually processed.
- Mock mode is **always** available: empty or invalid API keys never block the
  pipeline.

### 7.4 Actual run figures (this dataset)

- Requested: 50 / 8 469 tickets.
- Mode: MOCK (no API key).
- `_genai_status`: 50 rows == `'ok'` (all mock validations passed).
- Output: `outputs/genai_results/genai_ticket_analysis.csv`, 50 rows × 6
  content columns + ticket_id + _genai_status.

## 8. Power BI Dashboard Design

Full spec: `powerbi/dashboard_documentation.md`.

### 8.1 Data model

Single-table star:

- **Fact**: `tickets` (grain = 1 row per ticket). Load from
  `data/processed/cleaned_tickets.csv`, all 8 469 rows.
- **Optional**: `genai_results` (from `outputs/genai_results/...`) joined to
  `tickets` on `ticket_id` (1:0..1). Relationships single-direction filters
  from `tickets` to `genai_results`.

### 8.2 Pages

1. **Executive Overview** — 5 KPI cards + 4 visuals (count, donut, line, status).
2. **Ticket Analysis** — category/product/priority × volume and × resolution time.
3. **Resolution Analysis** — histogram, slowest categories, unresolved by product,
   High/Critical drill-through table.
4. **GenAI Insights** — cards + table: GenAI summary, category, priority,
   cause, suggested resolution.

### 8.3 DAX measure library (7 measures)

```dax
Resolved Tickets =
  CALCULATE(COUNTROWS(tickets),
    LOWER(TRIM(tickets[ticket_status])) IN {"closed","resolved"})

Unresolved Tickets = COUNTROWS(tickets) - [Resolved Tickets]

High/Critical Tickets =
  CALCULATE(COUNTROWS(tickets),
    tickets[ticket_priority] IN {"High","Critical"})

Avg Resolution Hours = AVERAGE(tickets[resolution_time_hours])

Median Resolution Hours = MEDIAN(tickets[resolution_time_hours])

Resolution Rate % =
  DIVIDE([Resolved Tickets], COUNTROWS(tickets), 0)

SLA Breach Risk (≥ 8h) =
  CALCULATE(COUNTROWS(tickets), tickets[resolution_time_hours] >= 8)
```

## 9. Results Summary

End-to-end verified results:

- **Cleaning input → output**: 8 469 → 8 469 rows (100 % retained; 0 dupes, 0 invalid).
- **SQL load**: 8 469 rows into `tickets` table; 10 queries all returned rows
  (0 failed).
- **Unresolved load**: 5 700 rows in backlog (67.3 %).
- **GenAI**: 50 tickets, MOCK mode, 50 valid structured JSON rows, 0 API errors.
- **Tests**: 26 / 26 passed in ~0.26 s (pytest).
- **Reports**: data_quality_report, business_insights, sql_query_results,
  final_project_report, final_project_audit, resume_bullets all written to
  `outputs/reports/`.
- **Dashboard**: 4-page Power BI specification delivered.

## 10. Limitations

1. **Sample dataset**: 8 469 tickets, limited time range. Any claims derived
   from it apply only to this sample.
2. **GenAI is advisory only**. `suggested_priority` is named explicitly to
   distinguish it from the ground-truth `ticket_priority` column. No output
   should be executed as a production change without human sign-off.
3. **Single-table design** keeps the project reproducible and portable, but
   real deployment likely needs `DIM_*` tables (customer, product, agent,
   team, SLA policy).
4. **CSAT sparsity**: satisfaction rating has NaN rows. Per-segment CSAT
   averages are valid only inside the observed subset.
5. **First-Response-Timestamp SLA** is not fully enforceable without an SLA
   policy dimension table.
6. **SQLite**: project runs on SQLite for reproducibility; equivalent MySQL
   scripts are documented but not executed against a live instance.

## 11. Future Improvements

1. **Full dimensional warehouse**: add `customer_dim`, `product_dim`,
   `agent_dim`, `sla_policy_dim` tables; restructure `tickets` fact with FKs.
2. **ML ticket classifier**: train a baseline (TF-IDF → LinearSVC) on
   `(Ticket Subject + Description) → Ticket Type`; benchmark against GenAI
   categorisation.
3. **Unsupervised cluster analysis**: k-means on description embeddings to
   surface emergent ticket groups.
4. **Semantic search + nearest-ticket retrieval**: embed historical
   resolutions and return the 3 most similar past tickets to accompany the
   GenAI suggestion.
5. **Interactive Streamlit / Gradio UI**: paste one ticket; receive GenAI
   summary + similar historical tickets + links to KB articles.
6. **Live MySQL instance + scheduler**: `cron` / Airflow DAG that runs the
   pipeline daily and refreshes Power BI via on-premises data gateway.
7. **Cost attribution**: join with billing data to estimate `cost per ticket
   category / channel / priority`; produce a support P&L.
