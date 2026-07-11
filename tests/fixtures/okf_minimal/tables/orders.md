---
type: BigQuery Table
title: Orders
description: One row per completed customer order.
resource: https://console.cloud.google.com/bigquery?p=fixture&d=sales&t=orders
tags: [sales, orders]
timestamp: 2026-07-11T00:00:00Z
---

# Schema

| Column        | Type      | Description                              |
|---------------|-----------|------------------------------------------|
| `order_id`    | STRING    | Unique order identifier.                 |
| `customer_id` | STRING    | FK to [customers](/tables/customers.md). |
| `total_usd`   | NUMERIC   | Order total in USD.                      |
| `placed_at`   | TIMESTAMP | When the order was submitted.            |

Part of the [sales dataset](/datasets/sales.md).

# Citations

[1] [Fixture schema reference](https://example.com/schema/orders)
