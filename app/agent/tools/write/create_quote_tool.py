from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.proposal_adaptater import ProposalAdaptater


class CreateQuoteTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : WRITE — soumis à confirmation avant exécution (§3.2, §5.1).
    """

    name = "create_quote"
    sense = ToolSense.WRITE

    description = (
        "Crée un devis (proposition commerciale) pour un client Dolibarr (à l'état brouillon, validé "
        "ensuite par un utilisateur habilité dans Dolibarr). Chaque ligne doit contenir label, qty, price "
        "(prix unitaire HT) et vat (taux de TVA en %). APPELEZ cet outil pour toute demande de devis : "
        "l'action sera enregistrée en attente de confirmation de l'utilisateur avant toute écriture."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "client_id": {
                "type": "integer",
                "description": "Identifiant Dolibarr du client (via search_client)."
            },
            "lines": {
                "type": "array",
                "description": "Lignes du devis.",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "description": "Libellé / désignation."},
                        "qty": {"type": "number", "description": "Quantité (défaut 1)."},
                        "price": {"type": "number", "description": "Prix unitaire HT."},
                        "vat": {"type": "number", "description": "Taux de TVA en pourcentage (ex. 18, 0)."}
                    },
                    "required": ["label", "price"]
                }
            },
            "date": {"type": "string", "description": "Date du devis (AAAA-MM-JJ). Optionnelle (défaut : aujourd'hui)."},
            "validity_days": {"type": "integer", "description": "Durée de validité en jours (défaut 30)."},
            "note": {"type": "string", "description": "Note publique (optionnelle)."}
        },
        "required": ["client_id", "lines"]
    }

    @staticmethod
    def run(params: dict):
        try:
            return ProposalAdaptater.create(params)
        except Exception as e:
            logger.error(f"Error in CreateQuoteTool.run: {e}")
            return {"error": str(e)}
