---
type: BigQuery Table
title: Customers
description: One row per customer, with lifecycle segment.
resource: https://console.cloud.google.com/bigquery?p=fixture&d=sales&t=customers
tags: [sales, customers]
timestamp: 2026-07-11T00:00:00Z
---

# Schema

| Column        | Type   | Description                       |
|---------------|--------|-----------------------------------|
| `customer_id` | STRING | Unique customer identifier.       |
| `segment`     | STRING | Lifecycle segment (new/active/…). |

Joined from [orders](/tables/orders.md) on `customer_id`.
This link is intentionally broken for permissive-reader tests:
[churn model](/models/churn.md).
