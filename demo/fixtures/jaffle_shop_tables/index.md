---
okf_version: "0.1"
---

# jaffle-shop table catalog (demo)

Hand-authored OKF bundle documenting a few tables from
[dbt-labs/jaffle-shop](https://github.com/dbt-labs/jaffle-shop) — enough for
`okf-bridge link` to find real `ref()`-based edges against the cloned repo
(see [`../README.md`](../README.md)). Not exhaustive: jaffle-shop's staging
models also `source()` a handful of raw tables (`raw_orders`,
`raw_customers`, ...) that aren't cataloged here — the linker silently skips
`ref()`/`source()` targets with no matching table concept (MAPPING.md §4 L5),
so that's expected, not a bug.

* [Tables](tables/) - jaffle-shop mart and staging table concepts
