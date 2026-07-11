---
type: dbt Model
title: Staging Customers
description: Renamed and typed raw customers, sourced from the ecom.raw_customers seed.
resource: https://github.com/dbt-labs/jaffle-shop/blob/main/models/staging/stg_customers.sql
tags: [jaffle-shop, staging]
timestamp: 2026-07-11T00:00:00Z
---

Built by `models/staging/stg_customers.sql`, which selects from
`{{ source('ecom', 'raw_customers') }}`. Not further re-catalogued here — see
the bundle-level note in `../index.md`.

Consumed by [customers](/tables/customers.md).
