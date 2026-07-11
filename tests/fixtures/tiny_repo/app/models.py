"""Domain models for the tiny fixture app.

Deliberately exercises: class definitions, inheritance, docstrings,
and a rationale comment — all signals graphify extracts as nodes.
"""


class BaseModel:
    """Common persistence behaviour for all models."""

    table_name: str = ""

    def save(self) -> None:
        """Persist the model. # NOTE: simplified for the fixture."""


class Order(BaseModel):
    """One completed customer order."""

    table_name = "orders"

    def __init__(self, order_id: str, total_usd: float) -> None:
        self.order_id = order_id
        self.total_usd = total_usd


class Customer(BaseModel):
    """A customer. Exact-name linker case: matches the 'customers' table."""

    table_name = "customers"
