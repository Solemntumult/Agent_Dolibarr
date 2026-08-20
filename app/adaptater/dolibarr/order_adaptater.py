"""Adaptateur commandes clients — lecture via l'API REST Dolibarr.

Points d'accès : /orders, /orders/{id}.
Statuts Dolibarr (field fk_statut) : 0 brouillon, 1 validée, 2 envoyée, 3 acceptée, 4 refusée, 5 facturée.
"""
from adaptater.dolibarr.dolibarr_client_adaptater import DolibarrClientAdaptater, DolibarrClientError
from commons.instances.instances import logger


class OrderAdaptater:

    @staticmethod
    def list_orders(status: str = None, limit: int = 100) -> list:
        """Liste les commandes. status: 'draft' | 'validated' | 'shipped' | 'all'."""
        try:
            params = {"limit": min(int(limit) or 100, 500), "sortfield": "t.date_commande", "sortorder": "DESC"}
            status_filter = {
                "draft": "(t.fk_statut:=:0)",
                "validated": "(t.fk_statut:=:1)",
                "shipped": "(t.fk_statut:=:3,4,5)",
            }.get(status)
            if status_filter:
                params["sqlfilters"] = status_filter
            raw_list = DolibarrClientAdaptater.get("orders", params=params)
            result = []
            for o in (raw_list if isinstance(raw_list, list) else []):
                result.append({
                    "id": o.get("id"),
                    "ref": o.get("ref"),
                    "client_id": o.get("socid"),
                    "total_ttc": float(o.get("total_ttc") or 0),
                    "total_ht": float(o.get("total_ht") or 0),
                    "date": o.get("date_commande"),
                    "status": o.get("fk_statut"),
                    "status_label": OrderAdaptater._status_label(o.get("fk_statut")),
                })
            return result
        except DolibarrClientError as e:
            logger.error(f"OrderAdaptater.list_orders failed: {e}")
            raise e

    @staticmethod
    def count_by_status() -> dict:
        """Retourne les comptages de commandes par statut."""
        try:
            all_orders = OrderAdaptater.list_orders(limit=500)
            counts = {"draft": 0, "validated": 0, "shipped": 0, "total": len(all_orders)}
            for o in all_orders:
                s = o.get("status", -1)
                if s == 0:
                    counts["draft"] += 1
                elif s in (1, 2):
                    counts["validated"] += 1
                elif s in (3, 4, 5):
                    counts["shipped"] += 1
            return counts
        except DolibarrClientError as e:
            logger.warning(f"OrderAdaptater.count_by_status failed: {e}")
            return {"draft": 0, "validated": 0, "shipped": 0, "total": 0, "error": str(e)}

    @staticmethod
    def _status_label(status) -> str:
        labels = {0: "Brouillon", 1: "Validée", 2: "Envoyée", 3: "Acceptée", 4: "Refusée", 5: "Facturée"}
        return labels.get(status, "Inconnu")
