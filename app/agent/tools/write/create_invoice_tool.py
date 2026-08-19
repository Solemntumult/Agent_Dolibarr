from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.invoice_adaptater import InvoiceAdaptater


class CreateInvoiceTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : WRITE — soumis à confirmation avant exécution (§3.2, §5.1).
    """

    name = "create_invoice"
    sense = ToolSense.WRITE

    description = (
        "Crée une facture client dans Dolibarr (à l'état brouillon, validée ensuite par un utilisateur "
        "habilité dans Dolibarr). Chaque ligne doit contenir label, qty, price (prix unitaire HT) et "
        "vat (taux de TVA en %, ex. 18 ou 0). APPELEZ cet outil pour toute demande de facture : "
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
                "description": "Lignes de la facture.",
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
            "date": {"type": "string", "description": "Date de la facture (AAAA-MM-JJ). Optionnelle (défaut : aujourd'hui)."},
            "ref_client": {"type": "string", "description": "Référence côté client (optionnelle)."},
            "note": {"type": "string", "description": "Note publique (optionnelle)."}
        },
        "required": ["client_id", "lines"]
    }

    @staticmethod
    def run(params: dict):
        try:
            return InvoiceAdaptater.create(params)
        except Exception as e:
            logger.error(f"Error in CreateInvoiceTool.run: {e}")
            return {"error": str(e)}
