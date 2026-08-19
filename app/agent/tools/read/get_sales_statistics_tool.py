from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.invoice_adaptater import InvoiceAdaptater


class GetSalesStatisticsTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : READ
    """

    name = "get_sales_statistics"
    sense = ToolSense.READ

    description = (
        "Calcule le chiffre d'affaires facturé sur une période (mois, trimestre, semestre, année) et le "
        "compare à la période précédente. Retourne le total TTC, le nombre de factures, l'évolution en "
        "pourcentage et les 5 meilleurs clients de la période. "
        "Utilisez-le pour répondre aux questions de type 'Quel est mon chiffre d'affaires du mois ?', "
        "'Compare le CA de ce mois à celui du mois dernier', 'Quels sont mes meilleurs clients ?'."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "enum": ["mois", "trimestre", "semestre", "annee"],
                "description": "Période à analyser (défaut 'mois')."
            }
        },
        "required": []
    }

    @staticmethod
    def run(params: dict):
        try:
            period = params.get("period", "mois")
            return InvoiceAdaptater.get_sales_statistics(period=period)
        except Exception as e:
            logger.error(f"Error in GetSalesStatisticsTool.run: {e}")
            return {"error": str(e)}
