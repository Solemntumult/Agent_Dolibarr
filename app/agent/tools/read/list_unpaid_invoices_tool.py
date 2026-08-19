from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.invoice_adaptater import InvoiceAdaptater


class ListUnpaidInvoicesTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : READ
    """

    name = "list_unpaid_invoices"
    sense = ToolSense.READ

    description = (
        "Retourne la liste des factures clients impayées (factures validées non réglées), avec le "
        "montant restant dû, la date d'échéance et le nombre de jours de retard. "
        "Filtre optionnel sur le nombre minimal de jours de retard (ex. 'factures impayées de plus de 30 jours')."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "jours_retard_min": {
                "type": "integer",
                "description": "Ne garder que les factures dont le retard (jours) dépasse ce nombre. Optionnel."
            },
            "client_id": {
                "type": "integer",
                "description": "Limiter aux factures d'un client précis (identifiant Dolibarr). Optionnel."
            }
        },
        "required": []
    }

    @staticmethod
    def run(params: dict):
        try:
            days = params.get("jours_retard_min", 0)
            client_id = params.get("client_id")
            return {"factures_impayees": InvoiceAdaptater.get_unpaid(min_days_late=days, client_id=client_id)}
        except Exception as e:
            logger.error(f"Error in ListUnpaidInvoicesTool.run: {e}")
            return {"error": str(e)}
