# INTERVIEW PREPARATION

This document groups likely interview questions for this portfolio project.
Answers reference **actual implementation details and actual numbers** — no
fabrication.

---

## SECTION A — Project Understanding

### Q1. Tell me about this project in 60 seconds.

> It is an end-to-end portfolio project named *GenAI IT Ticket Analytics &
> Resolution Assistant*. I take a raw CSV of 8 469 customer support tickets,
> run a reproducible cleaning pipeline (dedupe, whitespace, categorical norm,
> date parsing, invalid-row drop, resolution-time derivation), compute
> category / priority / product / channel / time analyses, load everything
> into SQLite via SQLAlchemy and execute 10 analytical queries, then run a
> cost-controlled GenAI assistant on 50 tickets to produce structured
> summaries, categories, priority suggestions, possible causes and
> step-by-step resolution advice. Finally I deliver a 4-page Power BI
> dashboard specification, 26 pytest tests, and all reports. The final
> headline figures: 2 769 resolved vs 5 700 unresolved tickets, median
> resolution time 6.35 hours, average satisfaction 2.99/5.

### Q2. Why this project?

> Support ticket analytics is a classic and high-impact business problem:
> every mid-size company has a helpdesk and every helpdesk asks the same
> questions — what breaks most, what takes longest, which products cause
> most load, and what can we automate. Also, GenAI-first-line-support is a
> very active real-world product category, so combining structured
> analytics + LLM-first-line suggestions produces a portfolio piece that
> demonstrates both the data-science workflow *and* the AI workflow, plus
> the BI deliverable.

### Q3. What business questions does it answer?

> Concretely:
> 1. Backlog health — how many tickets are open / closed / unresolved?
> 2. Category & priority mix — what types drive load?
> 3. Product load — which SKUs produce the most tickets, and resolve
>    fastest/slowest?
> 4. Channel mix — which channels produce volume, which resolve fastest?
> 5. Time trend — is volume growing / shrinking month over month?
> 6. Unresolved risk — how many High/Critical are still open, and what
>    products/topics do they hit?
> 7. Knowledge automation — can GenAI draft a summary, category, priority,
>    cause, and resolution checklist for new tickets?

### Q4. What are the verified headline metrics?

> *Actual figures from the dataset run:*
>
> - 8 469 tickets total, 17 columns.
> - 5 ticket types, 4 priorities, 4 channels, 42 products, 8 028 distinct
>   customers.
> - Resolved 2 769, Unresolved 5 700 (67.3 % backlog), Open 2 819.
> - Avg res time: 7.58 h, median: 6.35 h, min/max: 0.00 / 23.47 h.
> - Critical tickets: 2 129; 1 403 still unresolved (65.9 %).
> - Top subject: Refund request, 576 tickets / 6.8 %.
> - Top product: Canon EOS, 240 tickets.
> - Slowest category: Refund request, 8.12 h avg.
> - Tests: 26 / 26 passed.
> - GenAI: 50 tickets processed in MOCK mode (no API key required).

---

## SECTION B — Python & Pandas

### Q5. Walk me through your cleaning pipeline in order.

> Seven stages in `src/data_cleaning.py::run_cleaning_pipeline`:
> 1. **Column presence guard** — abort if any of the 7 required columns are
>    missing.
> 2. **Dedupe by Ticket ID**, keep first.
> 3. **Whitespace strip** on every object column plus collapsing internal runs.
> 4. **Priority normalisation** — `.title().strip()`; values outside
>    {Low, Medium, High, Critical} → "Unclassified".
> 5. **Date coercion** for Purchase / First Response / Time-to-Resolution
>    with `errors='coerce'`; count bad parses.
> 6. **Invalid-row drop** — rows missing Ticket ID or Ticket Status.
> 7. **Derivations**: `resolution_time_hours = delta_hours(res, first)` with
>    a negative-to-NaN guard; `description_length = len(clean_text(desc))`.
>
> Each step records *before/after* counts in a `DataQualityReport` dataclass
> and everything is flushed to `outputs/reports/data_quality_report.txt`.

### Q6. What is `_is_unresolved(s)` and why did you need it?

> Pandas 2.3 removed the `na=` keyword argument from `Series.isin()`. Three
> of my analysis aggregations (category / priority / product breakdowns)
> used an inline lambda `lambda g: int(g['ticket_status'].isin(['Closed',
> 'Resolved'], na=False).sum())` and hit `TypeError: unexpected keyword
> argument 'na'`. I wrote a helper at `src/analysis.py:51-55` that normalises
> strings (fillna → str → strip → lower) then inverts
> `~norm.isin(["closed","resolved"])`. NaNs become empty string, fall into
> the unresolved count, and the helper works identically across all three
> aggregations. All 26 tests passed after the change.

### Q7. How do you handle negative `resolution_time_hours`?

> I derive it as `(Time_to_Resolution − First_Response_Time)` in hours via
> `_td_to_hours()`. If the arithmetic produces a negative number, I replace
> it with `NaN` and increment the `neg_resolution_count` counter in the
> DataQualityReport so the audit log shows how many were guard-railed. On
> this dataset the guard triggered 0 times.

### Q8. What tests cover cleaning?

> `tests/test_cleaning.py` — 10 tests: text cleaner collapses whitespace,
> safe date parser handles bad strings, `td_to_hours` works for NaT and
> positive/negative deltas, dedupe removes duplicates, whitespace
> normalisation strips object columns, priority canonicalisation rejects
> unknown, invalid-row drop works, negative resolution-time becomes NaN,
> full end-to-end pipeline type-checks output columns and preserves
> rowcount when the frame is valid, DataQualityReport captures all fields.

---

## SECTION C — SQL & Data Modelling

### Q9. Why one big `tickets` table instead of a star with DIM tables?

> Scope trade-off for a student portfolio project. A single fact table makes
> the deliverable reproducible with zero DB admin — anyone can clone the
> repo, `pip install -r requirements.txt`, then `python main.py` and get
> the exact same SQLite file and reports. DIM tables are listed as a future
> improvement: customer / product / agent / team / SLA policy dimensions
> would make a production warehouse and enable agent-workload forecasting.

### Q10. Show me the schema briefly.

> `tickets(ticket_id PK, 16 original columns + resolution_time_hours +
> description_length)`. 5 indexes:
> `tickets_ticket_type_idx / _priority / _status / _product /
> _first_response_time_idx`. Schema file: `sql/schema.sql`. Pandas
> `.to_sql(if_exists='replace', index=False)` via SQLAlchemy engine loads
> 8 469 rows. `sql/load_data.sql` documents equivalent MySQL `LOAD DATA
> INFILE ...` syntax.

### Q11. Which 10 analytical queries did you run?

> 01_total_ticket_count, 02_tickets_by_category (volume + % total),
> 03_tickets_by_priority (volume + avg res hrs), 04_tickets_by_product
> (top 15), 05_unresolved_tickets (priority-ordered), 06_avg_and_max_resolution_time
> (now AVG/MAX/MIN; MySQL comment adds MEDIAN), 07_high_priority_unresolved,
> 08_monthly_ticket_volume, 09_product_resolution_performance (top 20),
> 10_channel_performance. Results written to
> `outputs/reports/sql_query_results.txt`.

### Q12. SQLite versus MySQL?

> Pipeline default is SQLite because it is file-based and zero-config. All
> queries are written in portable dialect and I deliberately avoid
> `MEDIAN()` in query 06 (since SQLite lacks it) — replaced with `MIN()`;
> the MySQL-`MEDIAN()` variant is retained as a documented comment. The
> monthly query uses `STRFTIME('%Y-%m', …)` for SQLite and I keep the
> `DATE_FORMAT(…, '%Y-%m')` MySQL syntax commented in the `.sql` file.

### Q13. How do you order unresolved tickets meaningfully?

> `CASE ticket_priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN
> 'Medium' THEN 3 WHEN 'Low' THEN 4 ELSE 5 END, ticket_id`. That keeps
> Critical first regardless of collation, then ticket_id as stable
> secondary. Same technique used in queries 05 and 07.

---

## SECTION D — GenAI Component

### Q14. What does the GenAI component produce per ticket?

> Strictly a JSON object with five fields:
>
> | field | type |
> | - | - |
> | `summary` | str, 1–2 sentences |
> | `category` | enum: Technical / Billing / Cancellation / Refund / Product / Other |
> | `suggested_priority` | enum: Low / Medium / High / Critical |
> | `possible_cause` | paragraph |
> | `suggested_resolution` | numbered checklist |
>
> Validation enforces required keys and enum domains; validation failures
> fall back to the MOCK resolver.

### Q15. What safeguards?

> (a) Cost cap: `MAX_TICKETS_FOR_GENAI` env var, default 50, explicit
> logline "N/TOTAL processed". (b) Live path: 2 retries with exponential
> backoff; catches timeout, 429, generic APIError, any Exception.
> (c) Structured output guard: JSON fences are stripped, first balanced
> object extracted, required-keys + enum-domains validated.
> (d) **Mock fallback** is always available: empty key, invalid key, rate
> limit, bad JSON — anything abnormal returns the rule-based mock answer
> instead of aborting. (e) Semantic safety: priority field is *named*
> `suggested_priority` and documentation flags it as advisory, never
> ground truth.

### Q16. How does the MOCK resolver work offline?

> `_call_mock()` applies keyword rules on the concatenated Subject +
> Description (case-insensitive):
> - vpn, login, password, auth → VPN / auth troubleshooting steps.
> - bill, charge, invoice, payment → billing review & payment-method
>   checklist.
> - update, install, upgrade, setup, driver → installation/update
>   troubleshooting.
> - battery, charge, power → power & battery steps.
> - network, connect, wifi, vpn, internet → network diagnostic ladder.
> - else → generic "read ticket, reproduce, gather logs, check KB,
>   escalate if needed".
>
> Each branch returns a deterministic dict that passes structure and enum
> validation. The 50-ticket run produced 50 valid mock rows.

### Q17. Why not run GenAI on ALL 8 469 tickets?

> Two reasons: (1) *Cost control* — for a student portfolio, even
> gpt-3.5-turbo at ~$0.50/1M tokens is unnecessary; the correctness of the
> integration is what matters, and that is demonstrated with N=50.
> (2) *Rate limits and time* — processing nearly 9k tickets serially is
> slow; parallelism would need a semaphore and async client, which adds
> scope. The `MAX_TICKETS_FOR_GENAI` knob lets a reviewer trivially
> increase the cap if they supply an API key.

### Q18. Walk through the validation of a GenAI output.

> After the raw string is returned by either `_call_live` or
> `_call_mock`:
> 1. `_parse_json_safe()` strips triple-backtick fences and extracts the
>    first balanced `{...}` block with `json.JSONDecoder.raw_decode()`.
> 2. `_validate_genai_output(obj)` checks:
>    - all five required keys present;
>    - `category` in the 6-enum set;
>    - `suggested_priority` in the 4-enum set;
>    - three string fields are non-empty;
>    - returns True/False + reason string.
> 3. If validation fails: pipeline falls back to MOCK.
> 4. Pipeline stamps an extra `_genai_status: 'ok' | 'mock'` field on
>    every row so the final CSV clearly flags origin.

### Q19. What tests cover GenAI?

> `tests/test_genai.py` — 8 tests:
> - class construction defaults to MOCK without key.
> - prompt builder includes the text fields it must.
> - `_parse_json_safe` strips code fences and handles plain JSON.
> - validator accepts valid objects and rejects: missing keys, wrong
>   category enum, wrong priority enum, empty strings.
> - `_call_mock` returns dict + every enum value is in-domain.
> - `analyze_ticket` returns all required keys plus `_genai_status`.
> - `analyze_dataframe` produces correct N rows and adds the
>   `_genai_status` column.

---

## SECTION E — Power BI & Visualisation

### Q20. Describe your Power BI design.

> File `powerbi/dashboard_documentation.md`; 4 pages.
>
> 1. **Executive Overview** — 5 KPI cards (Total, Open, Resolved,
>    High/Critical, Avg Res Hrs) + Tickets by Type (bar), Tickets by
>    Priority (bar), Tickets by Status (donut), Tickets over time (line).
> 2. **Ticket Analysis** — count by Type / Product (Top 15) / Priority,
>    then avg resolution time by Type / Priority / Product.
> 3. **Resolution Analysis** — resolution-time histogram, unresolved
>    tickets by product, categories sorted by avg desc, High + Critical
>    unresolved drill-through table.
> 4. **GenAI Insights** — cards for GenAI-processed count + category mix +
>    priority mix, and a detailed table of (ticket_id, subject, summary,
>    category, suggested_priority, cause, suggested_resolution).
>
> Data model: single `tickets` table grain = 1 per ticket; optional 1:0..1
> relationship to `genai_results` on `ticket_id`.

### Q21. Which DAX measures did you ship?

> Seven measures:
>
> ```dax
> Resolved Tickets     = CALCULATE(COUNTROWS(tickets),
>                       LOWER(TRIM(tickets[ticket_status]))
>                       IN {"closed","resolved"})
> Unresolved Tickets   = COUNTROWS(tickets) - [Resolved Tickets]
> High/Critical Tickets = CALCULATE(COUNTROWS(tickets),
>                        tickets[ticket_priority] IN {"High","Critical"})
> Avg Resolution Hours = AVERAGE(tickets[resolution_time_hours])
> Median Resolution Hours = MEDIAN(tickets[resolution_time_hours])
> Resolution Rate %    = DIVIDE([Resolved Tickets],
>                       COUNTROWS(tickets), 0)
> SLA Breach Risk (≥ 8h) = CALCULATE(COUNTROWS(tickets),
>                           tickets[resolution_time_hours] >= 8)
> ```

### Q22. Which Power BI visuals do you use for which question?

> - "What is the overall load?" → Cards + KPI gauges (Page 1).
> - "Category / priority / channel mix?" → Stacked bar / column / donut.
> - "Time trend?" → Line chart with `month(first_response_time)` x-axis.
> - "Speed?" → Resolution-time histogram; category sorted by avg hrs (bar).
> - "Unresolved backlog drill-down?" → Table with Conditional Formatting by
>   ticket_priority (Page 3).
> - "GenAI results?" → Table showing raw LLM outputs + cards for counts.

---

## SECTION F — Results, Limitations, Improvements

### Q23. Which concrete results surprised you?

> Two: (1) 67.3 % (5 700 / 8 469) of tickets are still unresolved — a huge
> backlog. Within the Critical priority the ratio is even worse: 65.9 %
> still unresolved. (2) Average satisfaction is 2.99 / 5 — low, which
> motivates follow-up segmentation and First-Response tracking.

### Q24. What are the key business insights?

> From `outputs/reports/business_insights.txt` (actual figures):
>
> 1. Most common subject: Refund request (576 / 6.8 %) → self-service FAQ
>    or refund flow.
> 2. Critical backlog: 1 403 unresolved → immediate escalation queue.
> 3. Top product by load: Canon EOS, 240 tickets → targeted staffing / KB.
> 4. Slowest category: Refund request (8.12 h avg) → process bottleneck.
> 5. Largest monthly delta: +3 028.57 % May→Jun → staffing forecast.
> 6. Unresolved category hotspot: Cancellation request (1 179) →
>    automation of cancellation workflow.
> 7. Oper. improvements: standardise ticket subjects, build KB for top
>    subjects, investigate 2.99/5 CSAT, track First-Response SLA.

### Q25. What are the main limitations?

> (1) Sample dataset — 8 469 rows; not a whole-year whole-company set.
> (2) GenAI outputs are advisory; `suggested_priority` is explicitly
> named that to not collide with ground truth.
> (3) Single-table schema keeps the deliverable portable but a warehouse
> would use DIM tables.
> (4) CSAT sparsity — averages apply only inside the rated subset.
> (5) First-Response SLA can't be enforced end-to-end without an SLA
> policy dimension table.
> (6) SQLite default (MySQL scripts documented but not executed live).

### Q26. Three concrete future improvements you'd ship next?

> 1. **ML categorisation benchmark**: TF-IDF + LinearSVC to predict
>    `ticket_type` from Subject + Description; compare F1 to GenAI
>    categorisation on a labelled split.
> 2. **Dimensional warehouse + Airflow DAG**: refactor tickets fact with
>    customer / product / agent / SLA_policy DIMs; run nightly into MySQL
>    and refresh Power BI via gateway.
> 3. **Similar-ticket retrieval layer**: embed historical resolutions
>    with OpenAI embeddings or TF-IDF + cosine; append the 3 nearest
>    historical tickets to the GenAI suggestion and surface them in a
>    small Streamlit app where an agent can paste a ticket and get
>    summary + suggestions + similar past cases + KB links.

---

## SECTION G — Ethics & Productionisation

### Q27. How do you prevent GenAI outputs from being trusted blindly?

> Three layers:
> (A) **Naming**: the enum field is called `suggested_priority`, not
> `priority`, to distinguish it from the `ticket_priority` ground-truth
> column.
> (B) **Provenance**: every GenAI row gets `_genai_status ∈ {'ok','mock'}`
> and the pipeline logs the count.
> (C) **Documentation**: README, Project Documentation, and Dashboard doc
> all state that GenAI output is advisory and requires human sign-off.

### Q28. If this had PII (names, emails), what would you change?

> (1) `.gitignore` already excludes `data/raw/*` except `!*.gitkeep`, so
> PII never commits.
> (2) Add an explicit scrub step in cleaning: SHA-256 hash email (with
> per-deploy salt), drop free-text name, store a hashed_customer_id as the
> join key.
> (3) For GenAI prompt injection, use a scrubbed view of the ticket
> (subject + description with regex masks for email/phone/ZIP) instead of
> raw text.
> (4) Access controls on the SQLite / MySQL outputs: DB grants, never
> distribute the cleaned CSV in a public repo.

### Q29. How would you deploy this to production?

> Rough design:
> - **Storage**: S3/ADLS for raw CSVs; landing / cleaned zones partitioned
>   by date.
> - **Orchestration**: Airflow / Dagster daily DAG:
>   ingest → clean → load → EDA → SQL reports → GenAI → Power BI refresh
>   trigger.
> - **DB**: MySQL on RDS / Cloud SQL with star schema + DIM tables.
> - **GenAI**: async worker (Celery / Temporal) bounded by rate-limit
>   semaphores, response rows in `ticket_genai_outputs` table.
> - **BI**: on-premises data gateway or DirectQuery to the warehouse.
> - **Observability**: pytest on-commit, Great Expectations on every
>   cleaned batch, Slack alert if (a) rowcount deviates > 15 % or
>   (b) critical-unresolved ratio grows or (c) GenAI failure rate > 5 %.

### Q30. Why should I hire you based on this project alone?

> Because this single repo shows I can take a real raw dataset and
> **ship** every single stage of a production-shaped analytics+AI project:
> reproducible cleaning with audit log, statistical analysis, relational
> schema + 10 portable SQL queries, cost-controlled GenAI integration
> with retries + structured validation + offline fallback, 26 unit tests
> that actually pass, a 4-page Power BI specification, and GitHub-ready
> documentation (README, project doc, interview Q&A) that is full of
> verified numbers instead of claims. All of that runs end to end with a
> single command: `python main.py`.
