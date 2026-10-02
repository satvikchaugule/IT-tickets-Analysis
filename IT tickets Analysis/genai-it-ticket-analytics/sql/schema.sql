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
