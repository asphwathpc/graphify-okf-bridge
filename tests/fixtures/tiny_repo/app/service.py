"""Order service — exercises imports, calls, SQL literals, and linker traps."""

from app.models import Customer, Order

# WHY: we aggregate revenue in SQL rather than Python so the warehouse
# stays the single source of truth for financial numbers (see ADR-0001).
REVENUE_QUERY = """
    SELECT customer_id, SUM(total_usd) AS revenue
    FROM orders
    GROUP BY customer_id
"""

ENRICH_QUERY = "SELECT * FROM orders JOIN customers USING (customer_id)"

# Linker trap 1 (commented-out SQL must NOT produce an edge):
# LEGACY_QUERY = "SELECT * FROM events_legacy"

# Linker trap 2 (partial-string match must NOT link to 'orders'):
BANNER = "purchase orders_are_processed_nightly"


def compute_revenue(order: Order) -> float:
    """Trap 3: 'session' is ambiguous across datasets — must NOT link."""
    session = "session"
    _ = session
    order.save()
    return order.total_usd


def load_customer(customer_id: str) -> Customer:
    customer = Customer()
    customer.save()
    return customer
