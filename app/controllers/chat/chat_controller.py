from flask import g, request
from flask_jwt_extended import get_jwt_identity

from adaptater.conversation.conversation_adaptater import ConversationAdaptater
from agent.orchestrator.agent_orchestrator import AgentOrchestrator
from commons.helpers.custom_response import CustomResponse
from commons.instances.instances import logger


class ChatController:

    @staticmethod
    def send_message():
        """POST /api/chat/ — envoie un message à l'agent (canal web)."""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json() or {}
            message_text = (data.get("message") or "").strip()
            conversation_id = data.get("conversation_id")

            if not message_text:
                return CustomResponse.send_response(
                    message="Message vide !", success=False, status_code=422
                )
            if len(message_text) > 10000:
                return CustomResponse.send_response(
                    message="Message trop long (10 000 caractères max).", success=False, status_code=422
                )

            result = AgentOrchestrator.handle_message(
                user_id=user_id, conversation_id=conversation_id, message_text=message_text
            )
            return CustomResponse.send_response(
                message="OK", success=True, status_code=200, data=result
            )
        except RuntimeError as e:
            logger.error(f"ChatController.send_message runtime: {e}")
            return CustomResponse.send_response(message=str(e), success=False, status_code=503)
        except Exception as e:
            logger.error(f"Error in ChatController.send_message: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def new_conversation():
        """POST /api/chat/conversations — crée une nouvelle conversation."""
        try:
            user_id = int(get_jwt_identity())
            conversation = ConversationAdaptater.create(user_id=user_id, channel="web")
            return CustomResponse.send_response(
                message="Conversation créée", success=True, status_code=201,
                data=conversation.to_dict(),
            )
        except Exception as e:
            logger.error(f"Error in ChatController.new_conversation: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def list_conversations():
        """GET /api/chat/conversations — historique des conversations de l'utilisateur."""
        try:
            user_id = int(get_jwt_identity())
            conversations = ConversationAdaptater.list_by_user(user_id)
            return CustomResponse.send_response(
                message="OK", success=True, status_code=200, data=conversations
            )
        except Exception as e:
            logger.error(f"Error in ChatController.list_conversations: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def list_messages(conversation_id):
        """GET /api/chat/conversations/<id>/messages — messages d'une conversation."""
        try:
            user_id = int(get_jwt_identity())
            conversation = ConversationAdaptater.get_by_id(conversation_id)
            if not conversation or conversation.user_id != user_id:
                return CustomResponse.send_response(
                    message="Conversation introuvable.", success=False, status_code=404
                )
            messages = ConversationAdaptater.get_messages(conversation_id)
            return CustomResponse.send_response(
                message="OK", success=True, status_code=200, data=messages
            )
        except Exception as e:
            logger.error(f"Error in ChatController.list_messages: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def rename_conversation(conversation_id):
        """PUT /api/chat/conversations/<id> — renomme une conversation (libellé)."""
        try:
            user_id = int(get_jwt_identity())
            conversation = ConversationAdaptater.get_by_id(conversation_id)
            if not conversation or conversation.user_id != user_id:
                return CustomResponse.send_response(
                    message="Conversation introuvable.", success=False, status_code=404
                )
            data = request.get_json() or {}
            title = (data.get("title") or "").strip()
            if not title:
                return CustomResponse.send_response(
                    message="Le libellé est vide.", success=False, status_code=422
                )
            if not ConversationAdaptater.update_title(conversation_id, title):
                return CustomResponse.send_response(
                    message="Impossible de renommer la conversation.", success=False, status_code=500
                )
            return CustomResponse.send_response(
                message="Conversation renommée.", success=True, status_code=200,
                data=ConversationAdaptater.get_by_id(conversation_id).to_dict(),
            )
        except Exception as e:
            logger.error(f"Error in ChatController.rename_conversation: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def delete_conversation(conversation_id):
        """DELETE /api/chat/conversations/<id> — supprime une conversation et ses messages."""
        try:
            user_id = int(get_jwt_identity())
            conversation = ConversationAdaptater.get_by_id(conversation_id)
            if not conversation or conversation.user_id != user_id:
                return CustomResponse.send_response(
                    message="Conversation introuvable.", success=False, status_code=404
                )
            if not ConversationAdaptater.delete(conversation_id):
                return CustomResponse.send_response(
                    message="Impossible de supprimer la conversation.", success=False, status_code=500
                )
            return CustomResponse.send_response(
                message="Conversation supprimée.", success=True, status_code=200
            )
        except Exception as e:
            logger.error(f"Error in ChatController.delete_conversation: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def dashboard():
        """GET /api/chat/dashboard — indicateurs clés pour le tableau de bord."""
        try:
            from adaptater.dolibarr.invoice_adaptater import InvoiceAdaptater
            from adaptater.dolibarr.proposal_adaptater import ProposalAdaptater
            from adaptater.dolibarr.product_adaptater import ProductAdaptater
            from agent.confirmation.confirmation_manager import ConfirmationManager

            user_id = int(get_jwt_identity())
            data = {"source": "dolibarr"}

            try:
                ca = InvoiceAdaptater.get_sales_statistics("mois")
                data["ca"] = {
                    "total_ttc": ca["current_period"]["total_ttc"],
                    "count": ca["current_period"]["count"],
                    "evolution_pct": ca.get("evolution_pct"),
                }
            except Exception as e:
                logger.warning(f"Dashboard CA indisponible: {e}")
                data["ca"] = {"error": str(e)}

            try:
                unpaid = InvoiceAdaptater.get_unpaid()
                data["unpaid"] = {
                    "count": len(unpaid),
                    "total_ttc": round(sum(float(u.get("total_ttc") or 0) for u in unpaid), 2),
                }
            except Exception as e:
                logger.warning(f"Dashboard impayés indisponibles: {e}")
                data["unpaid"] = {"error": str(e)}

            try:
                quotes = ProposalAdaptater.list_proposals("pending")
                data["quotes"] = {
                    "count": len(quotes),
                    "total_ttc": round(sum(float(q.get("total_ttc") or 0) for q in quotes), 2),
                }
            except Exception as e:
                logger.warning(f"Dashboard devis indisponibles: {e}")
                data["quotes"] = {"error": str(e)}

            try:
                stock = ProductAdaptater.get_stock_level()
                data["stock"] = {
                    "alert_count": stock.get("alert_count", 0),
                    "threshold": stock.get("threshold"),
                }
            except Exception as e:
                logger.warning(f"Dashboard stock indisponible: {e}")
                data["stock"] = {"error": str(e)}

            try:
                data["pending_confirmations"] = len(ConfirmationManager.list_pending(user_id=user_id))
            except Exception as e:
                logger.warning(f"Dashboard confirmations indisponibles: {e}")
                data["pending_confirmations"] = 0

            return CustomResponse.send_response(
                message="OK", success=True, status_code=200, data=data
            )
        except Exception as e:
            logger.error(f"Error in ChatController.dashboard: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def pending_actions():
        """GET /api/chat/pending — écritures en attente de confirmation pour cet utilisateur."""
        try:
            from agent.confirmation.confirmation_manager import ConfirmationManager
            user_id = int(get_jwt_identity())
            pending = ConfirmationManager.list_pending(user_id=user_id)
            return CustomResponse.send_response(
                message="OK", success=True, status_code=200, data=pending
            )
        except Exception as e:
            logger.error(f"Error in ChatController.pending_actions: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)
