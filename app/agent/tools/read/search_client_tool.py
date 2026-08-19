from commons.config.config import Config
from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.thirdparty_adaptater import ThirdpartyAdaptater
from services.vector.vector_store_service import VectorStoreService


class SearchClientTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : READ
    """

    name = "search_client"
    sense = ToolSense.READ

    description = (
        "Recherche des clients (tiers) dans Dolibarr par nom. "
        "Retourne la liste des tiers correspondants avec id, nom, email, téléphone et ville. "
        "Utilisez-le pour retrouver un client avant de créer un devis, une facture ou pour répondre "
        "à une question sur un client ('Donne-moi les coordonnées du client X')."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Nom (ou partie du nom) du client à rechercher. Laissez vide ou omettez pour lister tous les clients."
            },
            "limit": {
                "type": "integer",
                "description": "Nombre maximal de résultats (défaut 10)."
            }
        },
        "required": []
    }

    @staticmethod
    def run(params: dict):
        try:
            query = (params.get("query") or "").strip()
            limit = int(params.get("limit") or 10)

            if query and Config.VECTOR_SEARCH_ENABLED:
                hits = VectorStoreService.search("client", query, limit=limit)
                if hits:
                    clients = []
                    for hit in hits:
                        meta = dict(hit.get("metadata") or {})
                        meta["_vector_score"] = hit.get("score")
                        clients.append(meta)
                    return {
                        "clients": clients,
                        "_source": "vector_index",
                        "_hint": "Résultats issus de la recherche sémantique. Utilisez get_client(id) pour le détail complet.",
                    }

            return {"clients": ThirdpartyAdaptater.search(query=query, limit=limit), "_source": "dolibarr_api"}
        except Exception as e:
            logger.error(f"Error in SearchClientTool.run: {e}")
            return {"error": str(e)}
