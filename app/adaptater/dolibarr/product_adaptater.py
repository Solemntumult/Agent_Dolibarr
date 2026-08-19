"""Adaptateur produits / services — catalogue et niveaux de stock via l'API REST Dolibarr.

Points d'accès (cahier des charges §4.3) : /products, /products/{id}, /products/{id}/stock.
"""
from adaptater.dolibarr.dolibarr_client_adaptater import DolibarrClientAdaptater, DolibarrClientError
from commons.instances.instances import logger


class ProductAdaptater:

    @staticmethod
    def list_products(search: str = None, limit: int = 50, type_: str = None) -> list:
        """Liste le catalogue produits/services. type_: 'product' | 'service' | None."""
        try:
            params = {"limit": min(int(limit) or 50, 200), "sortfield": "t.ref", "sortorder": "ASC"}
            if search:
                params["sqlfilters"] = f"(t.label:like:%{search}%) OR (t.ref:like:%{search}%)"
            if type_ in ("product", "service"):
                params["type"] = type_
            raw_list = DolibarrClientAdaptater.get("products", params=params)
            result = []
            for p in raw_list if isinstance(raw_list, list) else []:
                result.append({
                    "id": p.get("id"),
                    "ref": p.get("ref"),
                    "label": p.get("label"),
                    "price_ttc": p.get("price_ttc"),
                    "price_ht": p.get("price_ht"),
                    "stock": p.get("stock_reel"),
                    "type": p.get("type"),
                })
            return result
        except DolibarrClientError as e:
            logger.error(f"ProductAdaptater.list_products failed: {e}")
            raise e

    @staticmethod
    def get_stock_level(product_id: int = None, threshold: float = None) -> dict:
        """Niveau de stock d'un produit précis ou de tous les produits.

        Retourne les produits dont le stock est inférieur au seuil dans 'below_threshold'.
        threshold: seuil d'alerte (par défaut : configuration agent, cf. §3.3).
        """
        try:
            if threshold is None:
                from adaptater.agent_config.agent_config_adaptater import AgentConfigAdaptater
                threshold = AgentConfigAdaptater.get_value("stock_alert_threshold", default=5)
            threshold = float(threshold)

            if product_id:
                raw = DolibarrClientAdaptater.get(f"products/{int(product_id)}/stock")
                items = [raw] if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
            else:
                items = ProductAdaptater.list_products(limit=200)

            levels = []
            below = []
            for p in items:
                stock = float(p.get("stock") or 0)
                item = {"id": p.get("id"), "ref": p.get("ref"), "label": p.get("label"), "stock": stock}
                levels.append(item)
                if stock < threshold:
                    below.append(item)
            return {"threshold": threshold, "levels": levels, "below_threshold": below,
                    "alert_count": len(below)}
        except DolibarrClientError as e:
            logger.error(f"ProductAdaptater.get_stock_level failed: {e}")
            raise e

    @staticmethod
    def get_by_id(product_id: int) -> dict:
        try:
            return DolibarrClientAdaptater.get(f"products/{int(product_id)}")
        except DolibarrClientError as e:
            logger.error(f"ProductAdaptater.get_by_id({product_id}) failed: {e}")
            raise e
