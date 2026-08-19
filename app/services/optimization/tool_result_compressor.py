"""Compression des résultats d'outils avant renvoi au LLM (réduction tokens)."""
from commons.config.config import Config


class ToolResultCompressor:

    LIST_KEYS = {
        "clients", "factures_impayees", "produits", "devis", "levels", "below_threshold",
    }

    @staticmethod
    def compress(tool_name: str, result: dict) -> dict:
        if not isinstance(result, dict):
            return result
        max_items = Config.LLM_TOOL_RESULT_MAX_ITEMS
        out = dict(result)

        if tool_name == "get_stock_level":
            return ToolResultCompressor._compress_stock(out, max_items)

        result_body = out.get("result")
        if isinstance(result_body, dict):
            compressed = ToolResultCompressor._compress_dict(result_body, max_items)
            out["result"] = compressed
        return out

    @staticmethod
    def _compress_stock(data: dict, max_items: int) -> dict:
        body = data.get("result") if "result" in data else data
        if not isinstance(body, dict):
            return data

        below = body.get("below_threshold") or []
        levels = body.get("levels") or []
        compressed = {
            "threshold": body.get("threshold"),
            "alert_count": body.get("alert_count", len(below)),
            "below_threshold": below[:max_items],
        }
        if len(levels) > max_items:
            compressed["_meta"] = {
                "levels_total": len(levels),
                "levels_omitted": True,
                "hint": "Utilisez product_id pour le détail d'un produit précis.",
            }
        else:
            compressed["levels"] = levels

        if "result" in data:
            data["result"] = compressed
            return data
        return compressed

    @staticmethod
    def _compress_dict(body: dict, max_items: int) -> dict:
        out = dict(body)
        for key, value in body.items():
            if key in ToolResultCompressor.LIST_KEYS and isinstance(value, list) and len(value) > max_items:
                out[key] = value[:max_items]
                out["_meta"] = {
                    "truncated": True,
                    "total": len(value),
                    "showing": max_items,
                    "list_key": key,
                }
        return out
