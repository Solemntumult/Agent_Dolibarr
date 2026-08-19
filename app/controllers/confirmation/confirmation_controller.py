from flask import g, request
from flask_jwt_extended import get_jwt_identity

from agent.confirmation.confirmation_manager import ConfirmationManager
from agent.orchestrator.agent_orchestrator import AgentOrchestrator
from commons.enums.user_roles.roles import UserRole
from commons.helpers.custom_response import CustomResponse
from commons.instances.instances import logger


class ConfirmationController:

    @staticmethod
    def list_pending():
        """GET /api/confirmation/pending — écritures en attente de confirmation."""
        try:
            user_id = int(get_jwt_identity())
            pending = ConfirmationManager.list_pending(user_id=user_id)
            return CustomResponse.send_response(
                message="OK", success=True, status_code=200, data=pending
            )
        except Exception as e:
            logger.error(f"Error in ConfirmationController.list_pending: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def get(confirmation_id):
        """GET /api/confirmation/<id> — détail d'une action en attente."""
        try:
            execution = ConfirmationManager.get(confirmation_id)
            if not execution:
                return CustomResponse.send_response(
                    message="Action introuvable.", success=False, status_code=404
                )
            return CustomResponse.send_response(
                message="OK", success=True, status_code=200, data=execution.to_dict()
            )
        except Exception as e:
            logger.error(f"Error in ConfirmationController.get: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def confirm(confirmation_id):
        """POST /api/confirmation/<id>/confirm — valide et exécute une écriture (§3.2, §5.1)."""
        try:
            user_id = int(get_jwt_identity())
            execution = ConfirmationManager.get(confirmation_id)
            if not execution:
                return CustomResponse.send_response(
                    message="Action introuvable.", success=False, status_code=404
                )
            if execution.confirmation_status != "pending":
                return CustomResponse.send_response(
                    message=f"Action déjà traitée (statut: {execution.confirmation_status}).",
                    success=False, status_code=409
                )
            # Droits (§5.1) : seul l'auteur de l'écriture (ou un administrateur) peut la confirmer.
            current_user = getattr(g, "current_user", None)
            is_admin = current_user and current_user.role == UserRole.ADMIN.value
            if execution.user_id not in (None, user_id) and not is_admin:
                return CustomResponse.send_response(
                    message="Accès refusé : cette action ne vous appartient pas.",
                    success=False, status_code=403
                )
            ConfirmationManager.confirm(confirmation_id, user_id)
            result = AgentOrchestrator.execute_confirmed(confirmation_id, user_id)
            return CustomResponse.send_response(
                message="Action confirmée et exécutée.", success=True, status_code=200, data=result
            )
        except Exception as e:
            logger.error(f"Error in ConfirmationController.confirm: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def download_document(confirmation_id):
        """GET /api/confirmation/<id>/document — télécharge le PDF du document créé (§4.4).

        Seul l'utilisateur qui a initié l'écriture (ou un administrateur) peut télécharger
        le PDF ; le document doit avoir été confirmé et généré (§5.1 droits respectés).
        """
        from io import BytesIO
        from flask import send_file
        from adaptater.dolibarr.document_adaptater import DocumentAdaptater
        from data.entities.tool_execution.tool_execution import ToolExecution
        from commons.enums.user_roles.roles import UserRole

        try:
            user_id = int(get_jwt_identity())
            execution = ConfirmationManager.get(confirmation_id)
            if not execution:
                return CustomResponse.send_response(
                    message="Action introuvable.", success=False, status_code=404
                )
            if execution.confirmation_status != "confirmed" or not execution.success:
                return CustomResponse.send_response(
                    message="Le document n'a pas été confirmé ou son exécution a échoué.",
                    success=False, status_code=403,
                )
            if execution.tool_name not in ("create_quote", "create_invoice"):
                return CustomResponse.send_response(
                    message="Aucun document PDF associé à cette action.",
                    success=False, status_code=404,
                )

            # Droits : l'auteur de l'écriture ou un administrateur (§5.1)
            current_user = getattr(g, "current_user", None)
            is_admin = current_user and current_user.role == UserRole.ADMIN.value
            if execution.user_id not in (None, user_id) and not is_admin:
                return CustomResponse.send_response(
                    message="Accès refusé à ce document.", success=False, status_code=403
                )

            document = (execution.result or {}).get("document") if isinstance(execution.result, dict) else None
            ref = (document or {}).get("ref") if isinstance(document, dict) else None
            if not ref:
                return CustomResponse.send_response(
                    message="Document PDF non disponible (référence manquante).",
                    success=False, status_code=404,
                )

            pdf = DocumentAdaptater.download_pdf(execution.tool_name, str(ref))
            pdf_bytes = DocumentAdaptater.pdf_bytes(pdf.get("content_base64", ""))
            filename = pdf.get("filename") or f"{ref}.pdf"
            return send_file(
                BytesIO(pdf_bytes),
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )
        except Exception as e:
            logger.error(f"Error in ConfirmationController.download_document: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def reject(confirmation_id):
        """POST /api/confirmation/<id>/reject — refuse une écriture."""
        try:
            user_id = int(get_jwt_identity())
            execution = ConfirmationManager.get(confirmation_id)
            if not execution:
                return CustomResponse.send_response(
                    message="Action introuvable.", success=False, status_code=404
                )
            # Droits (§5.1) : seul l'auteur (ou un administrateur) peut refuser l'écriture.
            current_user = getattr(g, "current_user", None)
            is_admin = current_user and current_user.role == UserRole.ADMIN.value
            if execution.user_id not in (None, user_id) and not is_admin:
                return CustomResponse.send_response(
                    message="Accès refusé : cette action ne vous appartient pas.",
                    success=False, status_code=403
                )
            rejected = ConfirmationManager.reject(confirmation_id, user_id)
            if not rejected:
                return CustomResponse.send_response(
                    message="Action introuvable.", success=False, status_code=404
                )
            return CustomResponse.send_response(
                message="Action refusée.", success=True, status_code=200
            )
        except Exception as e:
            logger.error(f"Error in ConfirmationController.reject: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)
