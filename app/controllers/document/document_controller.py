from io import BytesIO
from flask import send_file, request
from flask_jwt_extended import get_jwt_identity

from adaptater.dolibarr.document_adaptater import DocumentAdaptater, DolibarrClientError
from commons.helpers.custom_response import CustomResponse
from commons.instances.instances import logger


class DocumentController:

    @staticmethod
    def download(modulepart: str, ref: str):
        """GET /api/documents/<modulepart>/<ref> — télécharge le PDF officiel Dolibarr d'une facture ou d'un devis."""
        try:
            ref = str(ref).strip()
            modulepart = str(modulepart).strip().lower()

            if not ref or not modulepart:
                return CustomResponse.send_response(
                    message="Paramètres modulepart ou référence invalides.",
                    success=False,
                    status_code=422,
                )

            # 1. Tentative de génération/téléchargement direct via l'API documents Dolibarr
            pdf_data = None
            try:
                pdf_data = DocumentAdaptater.generate_pdf(modulepart, ref)
            except Exception as gen_err:
                logger.warning(f"DocumentController: generate_pdf a échoué ({gen_err}), tentative de download_pdf...")
                try:
                    pdf_data = DocumentAdaptater.download_pdf(modulepart, ref)
                except Exception as dl_err:
                    logger.error(f"DocumentController: téléchargement impossible: {dl_err}")
                    return CustomResponse.send_response(
                        message=f"Impossible de récupérer le document Dolibarr ({ref}): {dl_err}",
                        success=False,
                        status_code=404,
                    )

            content_base64 = (pdf_data or {}).get("content_base64")
            if not content_base64:
                return CustomResponse.send_response(
                    message="Contenu du document vide dans Dolibarr.",
                    success=False,
                    status_code=404,
                )

            pdf_bytes = DocumentAdaptater.pdf_bytes(content_base64)
            filename = (pdf_data or {}).get("filename") or f"{ref}.pdf"

            return send_file(
                BytesIO(pdf_bytes),
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )
        except Exception as e:
            logger.error(f"Error in DocumentController.download({modulepart}, {ref}): {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)
