-- dbt-style model: two ref() signals for the linker (known answers).
SELECT
    o.order_id,
    o.customer_id,
    o.total_usd,
    c.segment
FROM {{ ref('stg_orders') }} AS o
LEFT JOIN {{ source('warehouse', 'customers') }} AS c
    ON o.customer_id = c.customer_id
