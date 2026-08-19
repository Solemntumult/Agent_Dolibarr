"""Cache TTL des résultats d'outils de lecture (évite les appels Dolibarr + tokens répétés)."""
import hashlib
import json
import time

from commons.config.config import Config

_CACHEABLE_TOOLS = {
    "get_sales_statistics",
    "list_unpaid_invoices",
    "get_stock_level",
    "list_quotes",
    "list_products",
}


class QueryCacheService:

    _store = {}
    _hits = 0

    @staticmethod
    def _key(tool_name: str, params: dict) -> str:
        payload = json.dumps({"tool": tool_name, "params": params or {}}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def get(tool_name: str, params: dict):
        if not Config.QUERY_CACHE_ENABLED or tool_name not in _CACHEABLE_TOOLS:
            return None
        key = QueryCacheService._key(tool_name, params)
        entry = QueryCacheService._store.get(key)
        if not entry:
            return None
        if time.time() - entry["ts"] > Config.QUERY_CACHE_TTL_SECONDS:
            QueryCacheService._store.pop(key, None)
            return None
        QueryCacheService._hits += 1
        return entry["value"]

    @staticmethod
    def set(tool_name: str, params: dict, value: dict):
        if not Config.QUERY_CACHE_ENABLED or tool_name not in _CACHEABLE_TOOLS:
            return
        key = QueryCacheService._key(tool_name, params)
        QueryCacheService._store[key] = {"ts": time.time(), "value": value}
        if len(QueryCacheService._store) > 200:
            oldest = min(QueryCacheService._store, key=lambda k: QueryCacheService._store[k]["ts"])
            QueryCacheService._store.pop(oldest, None)

    @staticmethod
    def reset_hits():
        QueryCacheService._hits = 0

    @staticmethod
    def pop_hits() -> int:
        hits = QueryCacheService._hits
        QueryCacheService._hits = 0
        return hits
