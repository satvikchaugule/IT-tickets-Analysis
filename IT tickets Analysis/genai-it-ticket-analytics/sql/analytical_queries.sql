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
