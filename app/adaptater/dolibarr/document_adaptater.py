"""Adaptateur documents Dolibarr — génération et récupération des PDF (§4.4 « affichage des documents créés »).

Une fois un devis ou une facture créé (et confirmé, §3.2), l'agent peut générer son
document PDF via l'API REST Dolibarr :
- PUT /documents/builddoc   -> génère le PDF et le renvoie encodé en base64
- GET /documents/download   -> télécharge le PDF déjà généré (encodé en base64)

Les refs provisoires des brouillons (ex. "(PROV11)") sont acceptées par les deux
endpoints, ce qui permet de générer le PDF immédiatement après la confirmation.
"""
import base64

from adaptater.dolibarr.dolibarr_client_adaptater import DolibarrClientAdaptater, DolibarrClientError
from commons.instances.instances import logger

# Correspondance outil d'écriture / type -> modulepart de l'API documents
DOC_MODULEPART = {
    "create_quote": "propal",
    "create_invoice": "invoice",
    "convert_quote_to_invoice": "invoice",
    "quote": "propal",
    "invoice": "invoice",
    "propal": "propal",
}


class DocumentAdaptater:

    @staticmethod
    def modulepart_for_tool(tool_name: str) -> str:
        """Modulepart Dolibarr (propal / invoice / ...) pour un outil d'écriture donné."""
        return DOC_MODULEPART.get(tool_name)

    @staticmethod
    def generate_pdf(tool_name: str, ref: str, langcode: str = "fr_FR") -> dict:
        """Génère le PDF d'un devis/facture et le renvoie (base64) via PUT /documents/builddoc.

        Retourne {filename, content_type, filesize, content_base64, langcode} ou lève
        DolibarrClientError. La réf doit être le numéro exact côté Dolibarr (ex. "PR2608-0001"
        ou "(PROV11)" pour un brouillon).
        """
        modulepart = DocumentAdaptater.modulepart_for_tool(tool_name)
        if not modulepart:
            raise DolibarrClientError(f"Génération PDF non supportée pour l'outil {tool_name}.")
        if not ref:
            raise DolibarrClientError("Référence de document manquante pour la génération PDF.")

        original_file = f"{ref}/{ref}.pdf"
        data = {
            "modulepart": modulepart,
            "original_file": original_file,
            "langcode": langcode,
        }
        result = DolibarrClientAdaptater.put("documents/builddoc", data)
        if not isinstance(result, dict):
            raise DolibarrClientError(f"Réponse builddoc inattendue: {result}")

        content = result.get("content") or ""
        if not content:
            raise DolibarrClientError("Le document PDF n'a pas pu être généré (réponse vide).")
        return {
            "filename": result.get("filename") or f"{ref}.pdf",
            "content_type": result.get("content-type") or "application/pdf",
            "filesize": result.get("filesize"),
            "content_base64": content,
            "langcode": result.get("langcode") or langcode,
        }

    @staticmethod
    def download_pdf(tool_name: str, ref: str, langcode: str = "fr_FR") -> dict:
        """Télécharge un PDF déjà généré via GET /documents/download.

        Retourne {filename, content_type, filesize, content_base64} ou lève DolibarrClientError.
        """
        modulepart = DocumentAdaptater.modulepart_for_tool(tool_name)
        if not modulepart:
            raise DolibarrClientError(f"Téléchargement PDF non supporté pour l'outil {tool_name}.")
        if not ref:
            raise DolibarrClientError("Référence de document manquante pour le téléchargement PDF.")

        original_file = f"{ref}/{ref}.pdf"
        result = DolibarrClientAdaptater.get("documents/download", params={
            "modulepart": modulepart,
            "original_file": original_file,
            "langcode": langcode,
        })
        if not isinstance(result, dict) or not result.get("content"):
            raise DolibarrClientError("PDF introuvable dans Dolibarr.")
        return {
            "filename": result.get("filename") or f"{ref}.pdf",
            "content_type": result.get("content-type") or "application/pdf",
            "filesize": result.get("filesize"),
            "content_base64": result.get("content"),
        }

    @staticmethod
    def pdf_bytes(content_base64: str) -> bytes:
        """Décode le contenu base64 d'un PDF en octets."""
        try:
            return base64.b64decode(content_base64)
        except Exception as e:
            logger.error(f"DocumentAdaptater.pdf_bytes failed: {e}")
            raise DolibarrClientError("Contenu PDF invalide (base64).") from e
