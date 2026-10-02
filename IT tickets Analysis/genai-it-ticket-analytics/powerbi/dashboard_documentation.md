# Power BI Dashboard Design — "GenAI IT Ticket Analytics & Resolution Assistant"

This document is a build spec for the Power BI dashboard. Connect Power BI Desktop
to the cleaned dataset at `data/processed/cleaned_tickets.csv` (or the SQLite database
at `outputs/it_tickets.db` via `ODBC/SQLite ODBC Driver`, or import the CSV directly).

---

## Data Source

**Preferred source** (no DB setup needed):

- File: `data/processed/cleaned_tickets.csv`
- Encoding: UTF-8
- Delimiter: Comma
- Promoted headers: Yes

**Relational model (if using SQL)**:

- Fact table: `tickets` — one row per ticket.
  - Grain: 1 row = 1 ticket
  - Columns used: `ticket_id`, `ticket_type`, `ticket_priority`, `ticket_status`,
    `ticket_channel`, `product_purchased`, `customer_satisfaction_rating`,
    `first_response_time`, `resolution_timestamp`, `resolution_time_hours`,
    `ticket_description`, `ticket_subject`, `resolution`.
- Star schema is intentionally simple because the dataset is a single wide fact;
  dimensions (`ticket_type`, `ticket_priority`, `ticket_status`, `ticket_channel`,
  `product_purchased`) can be modeled in Power BI using `Create new table` or
  derived from the fact table for slicers.

### Important measures (DAX)

```dax
Total Tickets = COUNT(tickets[ticket_id])

Resolved Tickets =
    CALCULATE (
        [Total Tickets],
        KEEPFILTERS (
            tickets[ticket_status] IN { "Closed", "Resolved" }
        )
    )

Unresolved Tickets =
    CALCULATE (
        [Total Tickets],
        KEEPFILTERS (
            NOT tickets[ticket_status] IN { "Closed", "Resolved" }
        )
    )

High/Critical Tickets =
    CALCULATE (
        [Total Tickets],
        KEEPFILTERS (
            tickets[ticket_priority] IN { "High", "Critical" }
        )
    )

Avg Resolution Hours =
    CALCULATE (
        AVERAGE ( tickets[resolution_time_hours] ),
        NOT ISBLANK ( tickets[resolution_time_hours] )
    )

Median Resolution Hours =
    CALCULATE (
        MEDIAN ( tickets[resolution_time_hours] ),
        NOT ISBLANK ( tickets[resolution_time_hours] )
    )

Resolution Rate % =
    DIVIDE ( [Resolved Tickets], [Total Tickets], 0 )
```

---

## Page 1 — Executive Overview

Purpose: at-a-glance KPIs for managers and directors.

### KPIs (top row, 5 card visuals)

1. **Total Tickets** — `[Total Tickets]`
2. **Open Tickets** — `[Unresolved Tickets]`
3. **Resolved Tickets** — `[Resolved Tickets]`
4. **High / Critical Tickets** — `[High/Critical Tickets]`
5. **Average Resolution Time (hrs)** — `[Avg Resolution Hours]`

### Charts

| # | Visual | X / Axis | Y / Value | Legend |
|---|--------|----------|-----------|--------|
| 1 | Clustered bar chart | Ticket Type | Count of tickets | (none) |
| 2 | Clustered column chart | Ticket Priority | Count of tickets | (none) |
| 3 | Donut chart | Ticket Status | Count of tickets | (none) |
| 4 | Line chart | `First Response Time` -> Date hierarchy (Year / Month) | Count of tickets | (none) |

### Slicers (page-level)

- Ticket Priority (multi-select)
- Ticket Type (multi-select)
- First Response Time (date range slider)

---

## Page 2 — Ticket Analysis

Purpose: break tickets down by categorical dimensions.

| # | Visual | X / Axis | Y / Value | Purpose |
|---|--------|----------|-----------|---------|
| 1 | Clustered bar | Ticket Type | `[Total Tickets]` | Volume by category |
| 2 | Clustered bar | Ticket Type | `[Avg Resolution Hours]` | Speed by category |
| 3 | Clustered bar | Product Purchased (top 15 by count) | `[Total Tickets]` | Volume by product |
| 4 | Clustered bar | Product Purchased (top 15 by count) | `[Avg Resolution Hours]` | Speed by product |
| 5 | Clustered column | Ticket Priority | `[Avg Resolution Hours]` | Speed by priority tier |

---

## Page 3 — Resolution Analysis

Purpose: diagnose SLA and backlog health.

| # | Visual | X / Axis | Y / Value |
|---|--------|----------|-----------|
| 1 | Histogram / bar | Resolution Time Hours (bins: 0-4, 4-8, 8-24, 24+) | Count |
| 2 | Line and clustered column | Ticket Type | Column = total tickets, Line = `[Avg Resolution Hours]` |
| 3 | Clustered bar | Product Purchased | `[Unresolved Tickets]` |
| 4 | Table | Ticket ID, Type, Priority, Status, Subject, Product, Channel | Slicer: High/Critical + Unresolved |

Additional tooltip for table row: open the ticket description column.

---

## Page 4 — GenAI Insights

Purpose: showcase GenAI-assisted ticket analysis outputs.

Source table for this page: `outputs/genai_results/genai_ticket_analysis.csv`
(Join on `ticket_id` when both sources are loaded.)

### Layout

- Top left: **Card** — "Tickets processed by GenAI" = `COUNTROWS(genai_results)`
- Top middle: **Card** — "Model / Mode" = text box showing `MOCK` or `LIVE <model>`
- Top right: **Multi-row card** — category distribution of GenAI `suggested_priority`.

Middle section:

- **Table** with columns:
  - Ticket ID
  - Original Priority
  - Suggested Priority (GenAI)
  - Category (GenAI)
  - Summary (GenAI)
  - Possible Cause (GenAI)

Bottom section:

- **Text / narrative card** with drill-through context:
  - Selected ticket -> show full suggested resolution as a multi-line text field.

---

## Data Refresh Instructions (local development)

1. Run the end-to-end pipeline (`main.py`) so that the cleaned CSV and
   genai output CSV are regenerated.
2. In Power BI Desktop, open `Home > Transform data > Data source settings`
   and point the source files to the latest generated CSVs.
3. Click `Refresh`.

All page filters, slicers and measures will update automatically.

---

## File Import Checklist

- [ ] `data/processed/cleaned_tickets.csv` imported as `tickets` query.
- [ ] `outputs/genai_results/genai_ticket_analysis.csv` imported as `genai_results` (if exists).
- [ ] Relationship created: `tickets[ticket_id] 1:1 genai_results[ticket_id]` (single direction).
- [ ] All DAX measures defined under a dedicated `Measures` table.
- [ ] Pages renamed to `Executive Overview`, `Ticket Analysis`, `Resolution Analysis`, `GenAI Insights`.
- [ ] Report theme applied (e.g., `Power BI "City Park"` or a muted professional theme).
