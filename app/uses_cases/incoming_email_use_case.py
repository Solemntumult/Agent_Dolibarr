"""Use case : traitement des e-mails entrants (cahier des charges §3.5 U6, §4.5).

Lecture de la boîte dédiée (IMAP) → vérification de l'expéditeur (liste autorisée)
→ garde-fou anti-injection (contenu traité comme donnée) → réponse rédigée par le
LLM avec accès en lecture seule aux données Dolibarr → envoi de la réponse (SMTP).
Les e-mails d'expéditeurs non autorisés sont ignorés.
"""
from adaptater.audit.audit_log_adaptater import AuditLogAdaptater
from adaptater.conversation.conversation_adaptater import ConversationAdaptater
from agent.orchestrator.agent_orchestrator import AgentOrchestrator
from commons.instances.instances import logger
from services.email.imap_service import ImapService
from services.email.smtp_service import SmtpService
from services.security.prompt_guard_service import PromptGuardService


class IncomingEmailUseCase:

    @staticmethod
    def execute(task=None) -> dict:
        try:
            emails = ImapService.fetch_unseen(limit=20)
            processed = 0
            ignored = 0
            replies = 0

            for email_item in emails:
                sender = email_item.get("from_", "")
                subject = email_item.get("subject", "")
                body = email_item.get("body", "")

                guard = PromptGuardService.guard(body, sender=sender)
                if not guard["allowed"]:
                    ignored += 1
                    AuditLogAdaptater.create(
                        action="email_ignore", target_type="email",
                        details={"from": sender, "subject": subject[:100], "reason": guard["reason"]},
                        success=False,
                    )
                    ImapService.mark_seen(email_item["uid"])
                    continue

                # Conversation canal e-mail (user_id nullable) — historique des échanges
                conversation = ConversationAdaptater.create(user_id=None, channel="email",
                                                            title=subject[:80] or "E-mail entrant")
                ConversationAdaptater.add_message(conversation.id, "user",
                                                  f"De: {sender}\nSujet: {subject}\n\n{body}")

                try:
                    reply = AgentOrchestrator.answer_email_request(subject, guard["safe_body"])
                    sent = False
                    if SmtpService.is_configured():
                        sent = SmtpService.send(
                            to=sender,
                            subject=f"Re: {subject}" if subject else "Réponse de l'assistant ICT Consulting",
                            body=reply,
                        )
                    if sent:
                        replies += 1
                    ConversationAdaptater.add_message(conversation.id, "assistant", reply)
                    processed += 1
                    AuditLogAdaptater.create(
                        action="email_traite", target_type="email",
                        details={"from": sender, "subject": subject[:100], "suspicious": guard["suspicious"],
                                 "replied": sent},
                        success=True,
                    )
                except Exception as e:
                    logger.error(f"IncomingEmailUseCase traitement échec ({sender}): {e}")
                    AuditLogAdaptater.create(
                        action="email_erreur", target_type="email",
                        details={"from": sender, "subject": subject[:100], "error": str(e)},
                        success=False,
                    )
                finally:
                    ImapService.mark_seen(email_item["uid"])

            summary = f"{processed} e-mail(s) traité(s), {replies} réponse(s), {ignored} ignoré(s)"
            return {"summary": summary, "processed": processed, "replied": replies, "ignored": ignored}
        except Exception as e:
            logger.error(f"IncomingEmailUseCase.execute failed: {e}")
            raise e


UseCase = IncomingEmailUseCase
