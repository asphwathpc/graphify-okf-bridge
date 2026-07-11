---
type: dbt Model
title: Customers
description: One row per customer, built on top of stg_customers and orders.
resource: https://github.com/dbt-labs/jaffle-shop/blob/main/models/marts/customers.sql
tags: [jaffle-shop, marts]
timestamp: 2026-07-11T00:00:00Z
---

# Schema (approximate — see the dbt project for the authoritative source)

| Column           | Description                                |
|-------------------|---------------------------------------------|
| `customer_id`      | Unique customer identifier.                  |
| `customer_name`    | Customer's name.                             |
| `count_lifetime_orders` | Total orders placed, derived from [orders](/tables/orders.md). |

Built by `models/marts/customers.sql`, which selects from
`{{ ref('stg_customers') }}` and `{{ ref('orders') }}` — see
[staging customers](/tables/stg_customers.md) and [orders](/tables/orders.md).
