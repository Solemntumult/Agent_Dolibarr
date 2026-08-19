from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.proposal_adaptater import ProposalAdaptater
from adaptater.dolibarr.invoice_adaptater import InvoiceAdaptater


class ConvertQuoteToInvoiceTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : WRITE — soumis à confirmation avant exécution (§3.2, §5.1).
    """

    name = "convert_quote_to_invoice"
    sense = ToolSense.WRITE

    description = (
        "Transforme un devis (proposition commerciale) existant dans Dolibarr en une facture réelle dans Dolibarr. "
        "Récupère automatiquement le client et les lignes du devis dans Dolibarr pour générer la facture brouillon correspondante. "
        "APPELEZ cet outil dès que l'utilisateur demande de convertir ou transformer un devis en facture."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "quote_id": {
                "type": "string",
                "description": "Identifiant numérique (ex: 5) ou référence (ex: 'PR2608-0001') du devis à transformer."
            },
            "note": {
                "type": "string",
                "description": "Note publique additionnelle sur la facture (optionnelle)."
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

            quote = ProposalAdaptater.get_by_id_or_ref(quote_id)
            if not quote or not quote.get("id"):
                return {"error": f"Devis {quote_id} introuvable dans Dolibarr."}

            client_id = quote.get("client_id")
            if not client_id:
                return {"error": f"Client non trouvé pour le devis {quote_id}."}

            raw_lines = quote.get("lines") or []
            if not raw_lines:
                # Si les lignes détaillées ne sont pas dans le retour brut, on essaie de reconstituer une ligne avec le total
                total_ht = float(quote.get("total_ht") or 0)
                raw_lines = [{
                    "label": f"Facturation selon devis {quote.get('ref', quote_id)}",
                    "qty": 1,
                    "price": total_ht,
                    "vat": 18,
                }]

            invoice_lines = []
            for l in raw_lines:
                invoice_lines.append({
                    "label": l.get("label") or l.get("description") or f"Ligne devis {quote.get('ref')}",
                    "qty": float(l.get("qty", 1)),
                    "price": float(l.get("price") or l.get("subprice") or 0),
                    "vat": float(l.get("vat") or l.get("tva_tx") or 0),
                })

            invoice_data = {
                "client_id": int(client_id),
                "lines": invoice_lines,
                "ref_client": quote.get("ref", str(quote_id)),
                "note": params.get("note") or f"Facture issue du devis {quote.get('ref', quote_id)}",
            }

            created_invoice = InvoiceAdaptater.create(invoice_data)
            return {
                "message": f"Devis {quote.get('ref', quote_id)} transformé en facture avec succès dans Dolibarr.",
                "invoice": created_invoice,
                "quote_ref": quote.get("ref"),
                "client_id": client_id,
                "client_name": quote.get("client_name"),
            }
        except Exception as e:
            logger.error(f"Error in ConvertQuoteToInvoiceTool.run: {e}")
            return {"error": str(e)}
