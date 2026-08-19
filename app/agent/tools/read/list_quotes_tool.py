from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.proposal_adaptater import ProposalAdaptater


class ListQuotesTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : READ
    """

    name = "list_quotes"
    sense = ToolSense.READ

    description = (
        "Liste les devis (propositions commerciales) de Dolibarr, en particulier ceux en attente de "
        "validation client (statut 'pending'). Chaque devis retourne référence, client, montants et "
        "date de fin de validité. "
        "Utilisez-le pour répondre aux questions de type 'Combien de devis en attente de validation ?' "
        "ou 'Quels devis arrivent à expiration ?'."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["pending", "all"],
                "description": "Filtrer sur les devis en attente de validation client ('pending', défaut) ou tous ('all')."
            },
            "limit": {
                "type": "integer",
                "description": "Nombre maximal de résultats (défaut 100)."
            }
        },
        "required": []
    }

    @staticmethod
    def run(params: dict):
        try:
            status = params.get("status", "pending")
            limit = params.get("limit", 100)
            return {"devis": ProposalAdaptater.list_proposals(status=status, limit=limit)}
        except Exception as e:
            logger.error(f"Error in ListQuotesTool.run: {e}")
            return {"error": str(e)}
