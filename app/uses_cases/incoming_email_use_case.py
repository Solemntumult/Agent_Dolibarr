"""Use case : traitement des e-mails entrants (cahier des charges §3.5 U6, §4.5).

Lecture de la boîte dédiée (IMAP) → vérification de l'expéditeur (liste autorisée)
→ garde-fou anti-injection (contenu traité comme donnée) → analyse de la demande par l'agent IA
→ proposition d'actions logiques & projet de réponse → mise en attente de validation humaine (Human-in-the-Loop)
→ envoi de la réponse (SMTP) et exécution Dolibarr après validation par l'utilisateur.
"""
from datetime import datetime, timezone

from adaptater.audit.audit_log_adaptater import AuditLogAdaptater
from adaptater.conversation.conversation_adaptater import ConversationAdaptater
from adaptater.email.inbound_email_adaptater import InboundEmailAdaptater
from agent.orchestrator.agent_orchestrator import AgentOrchestrator
from commons.instances.instances import logger
from services.email.imap_service import ImapService
from services.security.prompt_guard_service import PromptGuardService


class IncomingEmailUseCase:

    @staticmethod
    def process_single_email(
        sender: str,
        subject: str,
        body: str,
        uid: str = None,
        recipient: str = None,
        sender_name: str = None,
    ) -> dict:
        """Traite et analyse un e-mail entrant (IMAP ou simulation)."""
        try:
            # 1. Vérification sécurité (liste blanche + prompt injection)
            guard = PromptGuardService.guard(body, sender=sender)
            safe_body = guard.get("safe_body", body)
            is_allowed = guard.get("allowed", True)
            is_suspicious = guard.get("suspicious", False)
            reason = guard.get("reason", "")

            # 2. Conversation associée
            conv = ConversationAdaptater.create(
                user_id=None,
                channel="email",
                title=subject[:80] if subject else "E-mail entrant"
            )
            ConversationAdaptater.add_message(
                conv.id,
                "user",
                f"De: {sender}\nSujet: {subject}\n\n{body}"
            )

            # 3. Si expéditeur non autorisé
            if not is_allowed:
                email_obj = InboundEmailAdaptater.create(
                    uid=uid,
                    sender=sender,
                    sender_name=sender_name,
                    recipient=recipient,
                    subject=subject,
                    body_raw=body,
                    body_clean=safe_body,
                    security_allowed=False,
                    security_suspicious=is_suspicious,
                    security_reason=reason or "Expéditeur non autorisé",
                    agent_summary="E-mail bloqué : l'expéditeur ne figure pas dans la liste des expéditeurs autorisés.",
                    status="ignored",
                    conversation_id=conv.id,
                )
                AuditLogAdaptater.create(
                    action="email_ignore",
                    target_type="email",
                    target_id=email_obj.id,
                    details={"from": sender, "subject": subject[:100], "reason": reason},
                    success=False,
                )
                return {"success": True, "email": email_obj.to_dict(), "status": "ignored"}

            # 4. Analyse IA de l'agent (avec outils de lecture Dolibarr)
            analysis = AgentOrchestrator.analyze_incoming_email(
                sender=sender,
                subject=subject,
                body=safe_body,
            )

            status = "suspicious" if is_suspicious else "pending_review"

            email_obj = InboundEmailAdaptater.create(
                uid=uid,
                sender=sender,
                sender_name=sender_name,
                recipient=recipient,
                subject=subject,
                body_raw=body,
                body_clean=safe_body,
                security_allowed=True,
                security_suspicious=is_suspicious,
                security_reason=reason,
                agent_summary=analysis.get("summary"),
                detected_intent=analysis.get("intent"),
                suggested_reply=analysis.get("suggested_reply"),
                suggested_action_type=analysis.get("suggested_action_type"),
                suggested_action_params=analysis.get("suggested_action_params"),
                suggested_action_label=analysis.get("suggested_action_label"),
                status=status,
                conversation_id=conv.id,
            )

            # Message assistant dans la conversation
            ConversationAdaptater.add_message(
                conv.id,
                "assistant",
                f"**Analyse de l'e-mail :** {analysis.get('summary')}\n\n"
                f"**Réponse proposée :**\n{analysis.get('suggested_reply')}"
            )

            AuditLogAdaptater.create(
                action="email_analyse",
                target_type="email",
                target_id=email_obj.id,
                details={
                    "from": sender,
                    "subject": (subject or "")[:100],
                    "intent": analysis.get("intent"),
                    "suspicious": is_suspicious,
                },
                success=True,
            )

            return {"success": True, "email": email_obj.to_dict(), "status": status}

        except Exception as e:
            logger.error(f"IncomingEmailUseCase.process_single_email failed ({sender}): {e}")
            raise e

    @staticmethod
    def execute(task=None) -> dict:
        """Exécution périodique ou manuelle : récupération des messages IMAP non lus."""
        try:
            emails = ImapService.fetch_unseen(limit=20)
            processed = 0
            ignored = 0
            pending = 0

            for email_item in emails:
                uid = str(email_item.get("uid"))
                # Vérifier si cet UID a déjà été enregistré
                existing = InboundEmailAdaptater.get_by_uid(uid)
                if existing:
                    ImapService.mark_seen(int(uid))
                    continue

                sender = email_item.get("from_", "")
                subject = email_item.get("subject", "")
                body = email_item.get("body", "")
                date_str = email_item.get("date", "")

                res = IncomingEmailUseCase.process_single_email(
                    sender=sender,
                    subject=subject,
                    body=body,
                    uid=uid,
                )

                if res.get("status") == "ignored":
                    ignored += 1
                else:
                    pending += 1
                    processed += 1

                ImapService.mark_seen(int(uid))

            summary = f"{processed} nouvel/nouveaux e-mail(s) analysé(s) en attente de validation, {ignored} ignoré(s)"
            return {
                "summary": summary,
                "processed": processed,
                "pending": pending,
                "ignored": ignored,
                "total_fetched": len(emails),
            }
        except Exception as e:
            logger.error(f"IncomingEmailUseCase.execute failed: {e}")
            raise e


UseCase = IncomingEmailUseCase
