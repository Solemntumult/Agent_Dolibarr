from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.proposal_adaptater import ProposalAdaptater


class GetQuoteTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : READ
    """

    name = "get_quote"
    sense = ToolSense.READ

    description = (
        "Retourne les informations détaillées d'un devis (proposition commerciale) Dolibarr "
        "(lignes, montants, statut, client, référence) à partir de son identifiant numérique ou de sa référence (ex. 'PR2608-0001')."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "quote_id": {
                "type": "string",
                "description": "Identifiant numérique (ex: 5) ou référence (ex: 'PR2608-0001' ou '(PROV8)') du devis."
            }
        },
        "required": ["quote_id"]
    }

    @staticmethod
    def run(params: dict):
        try:
            quote_id = params.get("quote_id")
            if not quote_id:
                return {"error": "Paramètre quote_id manquant."}
            return {"devis": ProposalAdaptater.get_by_id_or_ref(quote_id)}
        except Exception as e:
            logger.error(f"Error in GetQuoteTool.run: {e}")
            return {"error": str(e)}
