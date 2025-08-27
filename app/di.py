from __future__ import annotations
from .storage.memory import InMemoryStore

# Global store instance holder (set by app.main)
store_instance: InMemoryStore | None = None

def get_store() -> InMemoryStore:
    if store_instance is None:
        raise RuntimeError("Store not initialized")
    return store_instance
