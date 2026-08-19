from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.document_adaptater import DocumentAdaptater
from adaptater.dolibarr.invoice_adaptater import InvoiceAdaptater
from adaptater.dolibarr.proposal_adaptater import ProposalAdaptater


class GetDocumentTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : READ
    """

    name = "get_document"
    sense = ToolSense.READ

    description = (
        "Récupère le document officiel (PDF) généré par Dolibarr pour une facture ou un devis existant. "
        "Permet d'obtenir la référence officielle Dolibarr, les montants exacts et le lien de téléchargement direct du PDF généré par Dolibarr. "
        "APPELEZ cet outil dès que l'utilisateur demande : 'envoie-moi la facture', 'donne-moi le PDF', 'télécharger le devis', etc."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "doc_type": {
                "type": "string",
                "enum": ["invoice", "quote"],
                "description": "Type de document : 'invoice' (facture) ou 'quote' (devis)."
            },
            "ref_or_id": {
                "type": "string",
                "description": "Référence (ex: 'FA2608-0001', 'PR2608-0001') ou identifiant numérique (ex: 12) du document."
            }
        },
        "required": ["doc_type", "ref_or_id"]
    }

    @staticmethod
    def run(params: dict):
        try:
            doc_type = params.get("doc_type", "invoice")
            ref_or_id = str(params.get("ref_or_id") or "").strip()
            if not ref_or_id:
                return {"error": "Paramètre ref_or_id manquant."}

            tool_name = "create_invoice" if doc_type == "invoice" else "create_quote"
            modulepart = "invoice" if doc_type == "invoice" else "propal"

            # 1. Récupération des données réelles depuis Dolibarr
            if doc_type == "invoice":
                doc_info = InvoiceAdaptater.get_by_id_or_ref(ref_or_id)
            else:
                doc_info = ProposalAdaptater.get_by_id_or_ref(ref_or_id)

            if not doc_info or not doc_info.get("ref"):
                return {"error": f"Document {doc_type} '{ref_or_id}' introuvable dans Dolibarr."}

            ref = doc_info.get("ref")

            # 2. Vérification / génération du PDF officiel dans Dolibarr
            pdf_info = {}
            try:
                pdf_info = DocumentAdaptater.generate_pdf(tool_name, str(ref))
            except Exception as pdf_err:
                logger.warning(f"GetDocumentTool: builddoc a retourné une erreur (tentative download): {pdf_err}")
                try:
                    pdf_info = DocumentAdaptater.download_pdf(tool_name, str(ref))
                except Exception as dl_err:
                    logger.error(f"GetDocumentTool: impossible de récupérer le PDF Dolibarr: {dl_err}")

            filename = pdf_info.get("filename") or f"{ref}.pdf"
            download_url = f"/api/documents/{modulepart}/{ref}"

            return {
                "success": True,
                "doc_type": doc_type,
                "ref": ref,
                "id": doc_info.get("id"),
                "client_id": doc_info.get("client_id"),
                "client_name": doc_info.get("client_name"),
                "total_ht": doc_info.get("total_ht"),
                "total_ttc": doc_info.get("total_ttc"),
                "date": doc_info.get("date"),
                "due_date": doc_info.get("due_date"),
                "status": doc_info.get("status"),
                "filename": filename,
                "filesize": pdf_info.get("filesize"),
                "download_url": download_url,
                "is_official_dolibarr_document": True,
            }
        except Exception as e:
            logger.error(f"Error in GetDocumentTool.run: {e}")
            return {"error": str(e)}
