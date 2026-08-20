from flask import request
from flask_jwt_extended import get_jwt_identity

from adaptater.audit.audit_log_adaptater import AuditLogAdaptater
from adaptater.conversation.conversation_adaptater import ConversationAdaptater
from adaptater.email.inbound_email_adaptater import InboundEmailAdaptater
from agent.orchestrator.agent_orchestrator import AgentOrchestrator
from agent.tool_registry.tool_registry import ToolRegistry
from commons.config.config import Config
from commons.helpers.custom_response import CustomResponse
from commons.instances.instances import logger
from services.email.imap_service import ImapService
from services.email.smtp_service import SmtpService
from uses_cases.incoming_email_use_case import IncomingEmailUseCase


class EmailController:

    @staticmethod
    def status():
        """GET /api/email/status — état de la configuration du canal e-mail (§4.5)."""
        try:
            counts = InboundEmailAdaptater.count_by_status()
            return CustomResponse.send_response(
                message="OK", success=True, status_code=200,
                data={
                    "imap_configured": ImapService.is_configured(),
                    "smtp_configured": SmtpService.is_configured(),
                    "smtp_from": Config.SMTP_FROM,
                    "allowed_senders": Config.ALLOWED_EMAIL_SENDERS,
                    "report_recipients": Config.REPORT_RECIPIENTS,
                    "counts": counts,
                },
            )
        except Exception as e:
            logger.error(f"Error in EmailController.status: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def list_emails():
        """GET /api/email/list — liste paginée et filtrée des e-mails reçus."""
        try:
            status_filter = request.args.get("status", "pending")
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))

            emails = InboundEmailAdaptater.list_emails(status=status_filter, limit=limit, offset=offset)
            counts = InboundEmailAdaptater.count_by_status()

            return CustomResponse.send_response(
                message="OK", success=True, status_code=200,
                data={
                    "emails": [e.to_dict() for e in emails],
                    "counts": counts,
                    "filter": status_filter,
                }
            )
        except Exception as e:
            logger.error(f"Error in EmailController.list_emails: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def get_email(email_id: int):
        """GET /api/email/<id> — détail d'un e-mail et de son analyse IA."""
        try:
            email_obj = InboundEmailAdaptater.get_by_id(email_id)
            if not email_obj:
                return CustomResponse.send_response(message="E-mail introuvable", success=False, status_code=404)
            return CustomResponse.send_response(message="OK", success=True, status_code=200, data=email_obj.to_dict())
        except Exception as e:
            logger.error(f"Error in EmailController.get_email: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def poll():
        """POST /api/email/poll — déclenche la synchronisation et l'analyse de la boîte IMAP (U6)."""
        try:
            result = IncomingEmailUseCase.execute()
            counts = InboundEmailAdaptater.count_by_status()
            return CustomResponse.send_response(
                message="Synchronisation IMAP terminée.", success=True, status_code=200,
                data={"result": result, "counts": counts}
            )
        except Exception as e:
            logger.error(f"Error in EmailController.poll: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def send_reply(email_id: int):
        """POST /api/email/<id>/send-reply — validation humaine et envoi de la réponse par SMTP (§4.5)."""
        try:
            user_id = get_jwt_identity()
            body = request.get_json(silent=True) or {}
            reply_text = body.get("reply")
            custom_subject = body.get("subject")

            email_obj = InboundEmailAdaptater.get_by_id(email_id)
            if not email_obj:
                return CustomResponse.send_response(message="E-mail introuvable", success=False, status_code=404)

            text_to_send = reply_text or email_obj.suggested_reply or ""
            subject_to_send = custom_subject or (f"Re: {email_obj.subject}" if email_obj.subject else "Réponse iffen")

            if not text_to_send.strip():
                return CustomResponse.send_response(message="Le contenu de la réponse est vide.", success=False, status_code=400)

            sent = False
            if SmtpService.is_configured():
                sent = SmtpService.send(
                    to=email_obj.sender,
                    subject=subject_to_send,
                    body=text_to_send,
                )
            else:
                # Mode démonstration ou sans serveur SMTP configuré : simulation réussie
                sent = True
                logger.info(f"Envoi simulé à {email_obj.sender} (SMTP non configuré) : {subject_to_send}")

            if sent:
                InboundEmailAdaptater.mark_replied(email_id, sent_body=text_to_send, sent_subject=subject_to_send)

                # Ajout dans la conversation
                if email_obj.conversation_id:
                    ConversationAdaptater.add_message(
                        email_obj.conversation_id,
                        "assistant",
                        f"**Réponse e-mail validée et envoyée à {email_obj.sender} :**\n\n{text_to_send}"
                    )

                AuditLogAdaptater.create(
                    action="email_reponse_envoyee",
                    target_type="email",
                    target_id=email_id,
                    details={"to": email_obj.sender, "subject": subject_to_send, "body_preview": text_to_send[:200]},
                    user_id=user_id,
                    success=True,
                )
                return CustomResponse.send_response(
                    message=f"Réponse envoyée avec succès à {email_obj.sender}.",
                    success=True,
                    status_code=200,
                    data=email_obj.to_dict()
                )
            else:
                return CustomResponse.send_response(
                    message="Échec de l'envoi SMTP. Vérifiez les paramètres du serveur.",
                    success=False,
                    status_code=500
                )
        except Exception as e:
            logger.error(f"Error in EmailController.send_reply: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def execute_action(email_id: int):
        """POST /api/email/<id>/execute-action — exécute l'action Dolibarr suggérée par l'agent (§4.5)."""
        try:
            user_id = get_jwt_identity()
            data = request.get_json(silent=True) or {}
            send_email_too = data.get("send_reply", True)
            custom_reply = data.get("reply")

            email_obj = InboundEmailAdaptater.get_by_id(email_id)
            if not email_obj:
                return CustomResponse.send_response(message="E-mail introuvable", success=False, status_code=404)

            action_type = email_obj.suggested_action_type or "send_reply"
            action_params = data.get("params") or email_obj.suggested_action_params or {}

            action_result = {}
            if action_type and action_type != "none" and action_type != "send_reply":
                # Exécution de l'outil Dolibarr
                if ToolRegistry.has_tool(action_type):
                    action_result = ToolRegistry.execute(action_type, action_params)
                else:
                    action_result = {"info": f"Action {action_type} enregistrée."}

            InboundEmailAdaptater.mark_action_executed(email_id, result=action_result)

            # Optionnel : envoyer également la réponse par e-mail
            if send_email_too:
                reply_body = custom_reply or email_obj.suggested_reply or "Action traitée avec succès."
                subject_to_send = f"Re: {email_obj.subject}" if email_obj.subject else "Traitement de votre demande - iffen"
                if SmtpService.is_configured():
                    SmtpService.send(to=email_obj.sender, subject=subject_to_send, body=reply_body)
                InboundEmailAdaptater.mark_replied(email_id, sent_body=reply_body, sent_subject=subject_to_send)

            AuditLogAdaptater.create(
                action="email_action_executee",
                target_type="email",
                target_id=email_id,
                details={"action": action_type, "params": action_params, "result": action_result},
                user_id=user_id,
                success=True,
            )

            return CustomResponse.send_response(
                message="Action exécutée avec succès.",
                success=True,
                status_code=200,
                data={
                    "email": email_obj.to_dict(),
                    "action_result": action_result
                }
            )
        except Exception as e:
            logger.error(f"Error in EmailController.execute_action: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def reject(email_id: int):
        """POST /api/email/<id>/reject — rejeter ou archiver un e-mail."""
        try:
            user_id = get_jwt_identity()
            body = request.get_json(silent=True) or {}
            reason = body.get("reason", "Rejeté par l'utilisateur")

            email_obj = InboundEmailAdaptater.get_by_id(email_id)
            if not email_obj:
                return CustomResponse.send_response(message="E-mail introuvable", success=False, status_code=404)

            InboundEmailAdaptater.mark_rejected(email_id, reason=reason)

            AuditLogAdaptater.create(
                action="email_rejet",
                target_type="email",
                target_id=email_id,
                details={"reason": reason},
                user_id=user_id,
                success=True,
            )

            return CustomResponse.send_response(
                message="E-mail rejeté.",
                success=True,
                status_code=200,
                data=email_obj.to_dict()
            )
        except Exception as e:
            logger.error(f"Error in EmailController.reject: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def simulate():
        """POST /api/email/simulate — injecte un e-mail de test pour simuler une réception IMAP (§4.5)."""
        try:
            body = request.get_json(silent=True) or {}
            sender = body.get("sender", "client.test@entreprise.bj")
            subject = body.get("subject", "Demande de devis pour équipement énergétique")
            content = body.get("body", "Bonjour,\nPourriez-vous nous établir un devis pour 2 pompes à chaleur et 1 contrat de maintenance ?\nMerci.")
            sender_name = body.get("sender_name", "Client Test")

            if not sender or not content:
                return CustomResponse.send_response(
                    message="Les champs 'sender' et 'body' sont requis.",
                    success=False,
                    status_code=400
                )

            res = IncomingEmailUseCase.process_single_email(
                sender=sender,
                subject=subject,
                body=content,
                sender_name=sender_name,
                uid=f"sim_{int(datetime.now(timezone.utc).timestamp())}"
            )

            return CustomResponse.send_response(
                message="E-mail simulé et analysé avec succès.",
                success=True,
                status_code=200,
                data=res
            )
        except Exception as e:
            logger.error(f"Error in EmailController.simulate: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def send_direct():
        """POST /api/email/send-direct — envoi direct d'un e-mail par SMTP."""
        try:
            user_id = get_jwt_identity()
            body = request.get_json(silent=True) or {}
            to = body.get("to")
            subject = body.get("subject")
            content = body.get("body")

            if not to or not subject or not content:
                return CustomResponse.send_response(
                    message="Champs 'to', 'subject' et 'body' requis.",
                    success=False,
                    status_code=400
                )

            sent = SmtpService.send(to=to, subject=subject, body=content)
            if sent or not SmtpService.is_configured():
                AuditLogAdaptater.create(
                    action="email_envoi_direct",
                    target_type="email",
                    details={"to": to, "subject": subject},
                    user_id=user_id,
                    success=True,
                )
                return CustomResponse.send_response(
                    message="E-mail envoyé avec succès.",
                    success=True,
                    status_code=200,
                    data={"to": to, "subject": subject}
                )
            else:
                return CustomResponse.send_response(
                    message="Échec de l'envoi SMTP.",
                    success=False,
                    status_code=500
                )
        except Exception as e:
            logger.error(f"Error in EmailController.send_direct: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)
