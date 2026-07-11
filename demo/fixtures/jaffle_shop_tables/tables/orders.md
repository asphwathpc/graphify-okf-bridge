---
type: dbt Model
title: Orders
description: One row per customer order, built on top of stg_orders and order_items.
resource: https://github.com/dbt-labs/jaffle-shop/blob/main/models/marts/orders.sql
tags: [jaffle-shop, marts]
timestamp: 2026-07-11T00:00:00Z
---

# Schema (approximate — see the dbt project for the authoritative source)

| Column                 | Description                              |
|------------------------|-------------------------------------------|
| `order_id`             | Unique order identifier.                  |
| `customer_id`          | FK to [customers](/tables/customers.md).  |
| `ordered_at`           | When the order was placed.                |
| `order_cost`           | Sum of supply cost across order items.    |
| `is_food_order`        | Whether the order contains a food item.   |

Built by `models/marts/orders.sql`, which selects from
`{{ ref('stg_orders') }}` and `{{ ref('order_items') }}` — see
[staging orders](/tables/stg_orders.md).
