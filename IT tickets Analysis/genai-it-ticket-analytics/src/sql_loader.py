import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from utils import logger, ensure_dir


def _standardize_col(col: str) -> str:
    return (
        col.lower()
        .strip()
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "_")
        .replace("-", "_")
        .replace(".", "_")
    )


TICKET_COLUMN_MAP = {
    "Ticket ID": "ticket_id",
    "Customer Name": "customer_name",
    "Customer Email": "customer_email",
    "Customer Age": "customer_age",
    "Customer Gender": "customer_gender",
    "Product Purchased": "product_purchased",
    "Date of Purchase": "date_of_purchase",
    "Ticket Type": "ticket_type",
    "Ticket Subject": "ticket_subject",
    "Ticket Description": "ticket_description",
    "Ticket Status": "ticket_status",
    "Resolution": "resolution",
    "Ticket Priority": "ticket_priority",
    "Ticket Channel": "ticket_channel",
    "First Response Time": "first_response_time",
    "Time to Resolution": "resolution_timestamp",
    "resolution_time_hours": "resolution_time_hours",
    "description_length": "description_length",
}


def get_sqlite_engine():
    from sqlalchemy import create_engine
    ensure_dir(os.path.dirname(config.SQLITE_DB_PATH))
    url = f"sqlite:///{config.SQLITE_DB_PATH}"
    logger.info(f"Using SQLite engine at: {config.SQLITE_DB_PATH}")
    return create_engine(url)


def get_mysql_engine():
    from sqlalchemy import create_engine
    user = config.DB_USER
    pwd = config.DB_PASSWORD
    host = config.DB_HOST
    port = config.DB_PORT
    db = config.DB_NAME
    charset = "charset=utf8mb4"
    url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?{charset}"
    logger.info(f"Using MySQL engine: {host}:{port}/{db}")
    return create_engine(url)


def get_engine(prefer_mysql: bool = False):
    if prefer_mysql:
        try:
            return get_mysql_engine()
        except Exception as e:
            logger.warning(f"MySQL not available ({e}); falling back to SQLite.")
    return get_sqlite_engine()


def dataframe_to_sqlite(df: pd.DataFrame, engine=None, if_exists: str = "replace") -> None:
    if engine is None:
        engine = get_engine(prefer_mysql=False)
    out = df.copy()
    rename_map = {k: v for k, v in TICKET_COLUMN_MAP.items() if k in out.columns}
    out = out.rename(columns=rename_map)
    out.to_sql("tickets", con=engine, index=False, if_exists=if_exists, method="multi", chunksize=500)
    logger.info(f"Wrote {len(out)} rows to SQL table 'tickets'")


ANALYTICAL_QUERIES = {
    "01_total_ticket_count": """
        SELECT COUNT(*) AS total_tickets FROM tickets;
    """,
    "02_tickets_by_category": """
        SELECT ticket_type AS category,
               COUNT(*) AS ticket_count,
               ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM tickets), 2) AS pct_of_total
        FROM tickets
        GROUP BY ticket_type
        ORDER BY ticket_count DESC;
    """,
    "03_tickets_by_priority": """
        SELECT ticket_priority,
               COUNT(*) AS ticket_count,
               ROUND(AVG(CASE WHEN resolution_time_hours IS NOT NULL THEN resolution_time_hours END), 2) AS avg_resolution_hours
        FROM tickets
        GROUP BY ticket_priority
        ORDER BY
            CASE ticket_priority
                WHEN 'Critical' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3
                WHEN 'Low' THEN 4
                ELSE 5
            END;
    """,
    "04_tickets_by_product": """
        SELECT product_purchased,
               COUNT(*) AS ticket_count,
               ROUND(AVG(CASE WHEN resolution_time_hours IS NOT NULL THEN resolution_time_hours END), 2) AS avg_resolution_hours
        FROM tickets
        GROUP BY product_purchased
        ORDER BY ticket_count DESC
        LIMIT 15;
    """,
    "05_unresolved_tickets": """
        SELECT ticket_id, ticket_type, ticket_priority, ticket_status, ticket_subject, product_purchased
        FROM tickets
        WHERE LOWER(TRIM(ticket_status)) NOT IN ('closed','resolved')
        ORDER BY
            CASE ticket_priority
                WHEN 'Critical' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3
                WHEN 'Low' THEN 4
                ELSE 5
            END,
            ticket_id;
    """,
    "06_avg_and_max_resolution_time": """
        SELECT
            ROUND(AVG(resolution_time_hours), 2) AS avg_resolution_hours,
            ROUND(MAX(resolution_time_hours), 2) AS max_resolution_hours,
            ROUND(MIN(resolution_time_hours), 2) AS min_resolution_hours
        FROM tickets
        WHERE resolution_time_hours IS NOT NULL;
        -- Note for MySQL deployments, add the following column for median:
        -- ROUND(MEDIAN(resolution_time_hours), 2) AS median_resolution_hours
    """,
    "07_high_priority_unresolved": """
        SELECT ticket_id, ticket_type, ticket_priority, ticket_status, ticket_subject, product_purchased, ticket_channel
        FROM tickets
        WHERE LOWER(TRIM(ticket_status)) NOT IN ('closed','resolved')
          AND ticket_priority IN ('High','Critical')
        ORDER BY
            CASE ticket_priority WHEN 'Critical' THEN 1 ELSE 2 END,
            ticket_id;
    """,
    "08_monthly_ticket_volume": """
        SELECT
            STRFTIME('%Y-%m', first_response_time) AS ticket_month,
            COUNT(*) AS ticket_count
        FROM tickets
        WHERE first_response_time IS NOT NULL
        GROUP BY ticket_month
        ORDER BY ticket_month;
    """,
    "09_product_resolution_performance": """
        SELECT
            product_purchased,
            COUNT(*) AS total_tickets,
            SUM(CASE WHEN LOWER(TRIM(ticket_status)) IN ('closed','resolved') THEN 1 ELSE 0 END) AS resolved,
            ROUND(100.0 * SUM(CASE WHEN LOWER(TRIM(ticket_status)) IN ('closed','resolved') THEN 1 ELSE 0 END) / COUNT(*), 2) AS resolution_rate_pct,
            ROUND(AVG(CASE WHEN resolution_time_hours IS NOT NULL THEN resolution_time_hours END), 2) AS avg_resolution_hours
        FROM tickets
        GROUP BY product_purchased
        ORDER BY total_tickets DESC
        LIMIT 20;
    """,
    "10_channel_performance": """
        SELECT
            ticket_channel,
            COUNT(*) AS ticket_count,
            ROUND(AVG(CASE WHEN resolution_time_hours IS NOT NULL THEN resolution_time_hours END), 2) AS avg_resolution_hours
        FROM tickets
        GROUP BY ticket_channel
        ORDER BY ticket_count DESC;
    """,
}


def run_analytical_queries(engine=None) -> dict:
    if engine is None:
        engine = get_engine(prefer_mysql=False)
    results = {}
    logger.info(f"Running {len(ANALYTICAL_QUERIES)} analytical SQL queries")
    for name, q in ANALYTICAL_QUERIES.items():
        try:
            df_q = pd.read_sql_query(q, con=engine)
            results[name] = df_q
        except Exception as e:
            logger.warning(f"Query {name} failed: {e}")
            results[name] = pd.DataFrame({"error": [str(e)]})
    return results


def write_query_results_to_report(results: dict, filepath: str) -> None:
    ensure_dir(os.path.dirname(filepath))
    lines = []
    lines.append("=" * 70)
    lines.append("SQL ANALYTICAL QUERY RESULTS")
    lines.append("=" * 70)
    lines.append("")
    for name, df in results.items():
        lines.append(f"--- {name} ---")
        lines.append(df.to_string(index=False))
        lines.append("")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"SQL query report written to: {filepath}")


def write_sql_scripts() -> None:
    ensure_dir(config.SQL_DIR)
    schema_sql = """
-- schema.sql : IT Ticket Analytics Database Schema
-- Target: MySQL with SQLite fallback (kept mostly compatible)

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id               INTEGER PRIMARY KEY,
    customer_name           VARCHAR(160),
    customer_email          VARCHAR(200),
    customer_age            INTEGER,
    customer_gender         VARCHAR(40),
    product_purchased       VARCHAR(200),
    date_of_purchase        DATETIME,
    ticket_type             VARCHAR(100),
    ticket_subject          VARCHAR(255),
    ticket_description      TEXT,
    ticket_status           VARCHAR(80),
    resolution              TEXT,
    ticket_priority         VARCHAR(40),
    ticket_channel          VARCHAR(80),
    first_response_time     DATETIME,
    resolution_timestamp    DATETIME,
    resolution_time_hours   DECIMAL(12,2),
    description_length      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tickets_type     ON tickets(ticket_type);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(ticket_priority);
CREATE INDEX IF NOT EXISTS idx_tickets_status   ON tickets(ticket_status);
CREATE INDEX IF NOT EXISTS idx_tickets_product  ON tickets(product_purchased);
CREATE INDEX IF NOT EXISTS idx_tickets_created  ON tickets(first_response_time);
""".strip()

    load_sql = """
-- load_data.sql
-- Instructions:
-- 1. Run schema.sql to create tables.
-- 2. Use the CSV at data/processed/cleaned_tickets.csv
-- 3. Import via the src/sql_loader.py Python pipeline for SQLite.
-- 4. For MySQL, use LOAD DATA INFILE or mysqlimport after mapping columns:
--    Ticket ID            -> ticket_id
--    Customer Name        -> customer_name
--    Customer Email       -> customer_email
--    Customer Age         -> customer_age
--    Customer Gender      -> customer_gender
--    Product Purchased    -> product_purchased
--    Date of Purchase     -> date_of_purchase
--    Ticket Type          -> ticket_type
--    Ticket Subject       -> ticket_subject
--    Ticket Description   -> ticket_description
--    Ticket Status        -> ticket_status
--    Resolution           -> resolution
--    Ticket Priority      -> ticket_priority
--    Ticket Channel       -> ticket_channel
--    First Response Time  -> first_response_time
--    Time to Resolution   -> resolution_timestamp
--    resolution_time_hours-> resolution_time_hours
--    description_length   -> description_length
""".strip()

    queries_sql = """
-- analytical_queries.sql
-- 1. Total ticket count
SELECT COUNT(*) AS total_tickets FROM tickets;

-- 2. Tickets by category (ticket_type)
SELECT ticket_type AS category,
       COUNT(*) AS ticket_count,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM tickets), 2) AS pct_of_total
FROM tickets
GROUP BY ticket_type
ORDER BY ticket_count DESC;

-- 3. Tickets by priority
SELECT ticket_priority,
       COUNT(*) AS ticket_count,
       ROUND(AVG(resolution_time_hours), 2) AS avg_resolution_hours
FROM tickets
GROUP BY ticket_priority
ORDER BY
    CASE ticket_priority
        WHEN 'Critical' THEN 1
        WHEN 'High' THEN 2
        WHEN 'Medium' THEN 3
        WHEN 'Low' THEN 4
        ELSE 5
    END;

-- 4. Tickets by product (top 15)
SELECT product_purchased, COUNT(*) AS ticket_count
FROM tickets
GROUP BY product_purchased
ORDER BY ticket_count DESC
LIMIT 15;

-- 5. Unresolved tickets
SELECT ticket_id, ticket_type, ticket_priority, ticket_status, ticket_subject, product_purchased
FROM tickets
WHERE LOWER(TRIM(ticket_status)) NOT IN ('closed','resolved')
ORDER BY
    CASE ticket_priority
        WHEN 'Critical' THEN 1
        WHEN 'High' THEN 2
        WHEN 'Medium' THEN 3
        WHEN 'Low' THEN 4
        ELSE 5
    END,
    ticket_id;

-- 6. Average / max / median resolution time
SELECT
    ROUND(AVG(resolution_time_hours), 2)   AS avg_resolution_hours,
    ROUND(MAX(resolution_time_hours), 2)   AS max_resolution_hours,
    ROUND(MEDIAN(resolution_time_hours), 2) AS median_resolution_hours
FROM tickets
WHERE resolution_time_hours IS NOT NULL;

-- 7. High-priority unresolved tickets
SELECT ticket_id, ticket_type, ticket_priority, ticket_status, ticket_subject, product_purchased, ticket_channel
FROM tickets
WHERE LOWER(TRIM(ticket_status)) NOT IN ('closed','resolved')
  AND ticket_priority IN ('High','Critical')
ORDER BY
    CASE ticket_priority WHEN 'Critical' THEN 1 ELSE 2 END,
    ticket_id;

-- 8. Monthly ticket volume (SQLite)
SELECT STRFTIME('%Y-%m', first_response_time) AS ticket_month, COUNT(*) AS ticket_count
FROM tickets
WHERE first_response_time IS NOT NULL
GROUP BY ticket_month
ORDER BY ticket_month;

-- 9. Product-wise resolution performance
SELECT
    product_purchased,
    COUNT(*) AS total_tickets,
    SUM(CASE WHEN LOWER(TRIM(ticket_status)) IN ('closed','resolved') THEN 1 ELSE 0 END) AS resolved,
    ROUND(100.0 * SUM(CASE WHEN LOWER(TRIM(ticket_status)) IN ('closed','resolved') THEN 1 ELSE 0 END) / COUNT(*), 2) AS resolution_rate_pct,
    ROUND(AVG(resolution_time_hours), 2) AS avg_resolution_hours
FROM tickets
GROUP BY product_purchased
ORDER BY total_tickets DESC
LIMIT 20;

-- 10. Channel performance
SELECT
    ticket_channel,
    COUNT(*) AS ticket_count,
    ROUND(AVG(resolution_time_hours), 2) AS avg_resolution_hours
FROM tickets
GROUP BY ticket_channel
ORDER BY ticket_count DESC;
""".strip()

    for name, content in [
        ("schema.sql", schema_sql),
        ("load_data.sql", load_sql),
        ("analytical_queries.sql", queries_sql),
    ]:
        path = os.path.join(config.SQL_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content + "\n")
    logger.info(f"Wrote SQL scripts to {config.SQL_DIR}")


def run_sql_pipeline(df: pd.DataFrame) -> dict:
    logger.info("Running SQL pipeline...")
    write_sql_scripts()
    engine = get_engine(prefer_mysql=False)
    dataframe_to_sqlite(df, engine=engine, if_exists="replace")
    results = run_analytical_queries(engine)
    write_query_results_to_report(
        results, os.path.join(config.REPORTS_DIR, "sql_query_results.txt")
    )
    return {"engine": engine, "query_results": results}
