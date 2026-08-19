from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.invoice_adaptater import InvoiceAdaptater


class GetInvoiceTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : READ
    """

    name = "get_invoice"
    sense = ToolSense.READ

    description = (
        "Retourne les informations détaillées d'une facture client Dolibarr (lignes, montants, "
        "échéance, statut, référence) à partir de son identifiant numérique ou de sa référence (ex: 'FA2608-0001')."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "invoice_id": {
                "type": "string",
                "description": "Identifiant numérique (ex: 12) ou référence (ex: 'FA2608-0001' ou '(PROV11)') de la facture."
            }
        },
        "required": ["invoice_id"]
    }

    @staticmethod
    def run(params: dict):
        try:
            invoice_id = params.get("invoice_id")
            if not invoice_id:
                return {"error": "Paramètre invoice_id manquant."}
            return {"facture": InvoiceAdaptater.get_by_id_or_ref(invoice_id)}
        except Exception as e:
            logger.error(f"Error in GetInvoiceTool.run: {e}")
            return {"error": str(e)}
