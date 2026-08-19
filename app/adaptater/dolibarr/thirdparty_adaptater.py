"""Adaptateur tiers (clients/fournisseurs) — lecture et création via l'API REST Dolibarr.

Points d'accès (cahier des charges §4.3, Annexe B) : /thirdparties, /thirdparties/{id}.
"""
from adaptater.dolibarr.dolibarr_client_adaptater import DolibarrClientAdaptater, DolibarrClientError
from commons.instances.instances import logger
from data.schemas.thirdparty_schema import ThirdpartySchema


class ThirdpartyAdaptater:

    @staticmethod
    def search(query: str = None, limit: int = 10, type_: str = "customer") -> list:
        """Recherche un tiers par nom (sqlfilters). type_: customer | supplier | prospect | all."""
        try:
            params = {"limit": min(int(limit) or 10, 100), "sortfield": "t.nom", "sortorder": "ASC"}
            if query:
                params["sqlfilters"] = f"(t.nom:like:%{query}%)"
            if type_ and type_ != "all":
                params["type"] = type_
            raw_list = DolibarrClientAdaptater.get("thirdparties", params=params)
            return [ThirdpartySchema(raw).to_dict() for raw in raw_list if isinstance(raw, dict)]
        except DolibarrClientError as e:
            logger.error(f"ThirdpartyAdaptater.search failed: {e}")
            raise e

    @staticmethod
    def get_by_id(thirdparty_id: int) -> dict:
        try:
            raw = DolibarrClientAdaptater.get(f"thirdparties/{int(thirdparty_id)}")
            return ThirdpartySchema(raw).to_dict()
        except DolibarrClientError as e:
            logger.error(f"ThirdpartyAdaptater.get_by_id({thirdparty_id}) failed: {e}")
            raise e

    @staticmethod
    def create(data: dict) -> dict:
        """Crée un tiers (client). Retourne {'id': ...} renvoyé par Dolibarr."""
        try:
            if not data.get("name"):
                raise DolibarrClientError("Le nom du client est obligatoire.")
            payload = {
                "name": data.get("name"),
                "client": data.get("client", 1),  # 1 = client, 0 = fournisseur, 3 = les deux
                "address": data.get("address", ""),
                "zip": data.get("zip", ""),
                "town": data.get("city") or data.get("town", ""),
                "country_code": data.get("country_code", "BJ"),
                "phone": data.get("phone", ""),
                "email": data.get("email", ""),
                "url": data.get("url", ""),
                "note_public": data.get("note", ""),
            }
            result = DolibarrClientAdaptater.post("thirdparties", payload)
            thirdparty_id = result if isinstance(result, int) else (result.get("id") if isinstance(result, dict) else (int(result) if str(result).isdigit() else None))
            if not thirdparty_id:
                raise DolibarrClientError(f"Création du tiers sans identifiant retourné: {result}")
            return {"id": thirdparty_id, "name": data.get("name"), "email": data.get("email", "")}
        except DolibarrClientError as e:
            logger.error(f"ThirdpartyAdaptater.create failed: {e}")
            raise e
