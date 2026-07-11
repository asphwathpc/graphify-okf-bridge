---
type: dbt Model
title: Staging Orders
description: Renamed and typed raw orders, sourced from the ecom.raw_orders seed.
resource: https://github.com/dbt-labs/jaffle-shop/blob/main/models/staging/stg_orders.sql
tags: [jaffle-shop, staging]
timestamp: 2026-07-11T00:00:00Z
---

Built by `models/staging/stg_orders.sql`, which selects from
`{{ source('ecom', 'raw_orders') }}`. Not further re-catalogued here — see
the bundle-level note in `../index.md` on why some `source()` targets are
intentionally left uncatalogued for this demo.

Consumed by [orders](/tables/orders.md).
