"""Use case : relance automatique des factures impayées (cahier des charges §3.3, U3).

Pour chaque échéance configurée (J+7, J+15, J+30), les factures impayées arrivées
à cette échéance reçoivent un e-mail de relance rédigé par l'agent (modèle léger),
puis l'action est journalisée dans l'agenda Dolibarr et dans le journal d'audit.
"""
from adaptater.agent_config.agent_config_adaptater import AgentConfigAdaptater
from adaptater.audit.audit_log_adaptater import AuditLogAdaptater
from adaptater.dolibarr.agenda_event_adaptater import AgendaEventAdaptater
from adaptater.dolibarr.invoice_adaptater import InvoiceAdaptater
from adaptater.dolibarr.thirdparty_adaptater import ThirdpartyAdaptater
from commons.instances.instances import logger
from services.email.smtp_service import SmtpService
from services.openai.openai_service import OpenaiService


class UnpaidInvoiceReminderUseCase:

    @staticmethod
    def _get_thresholds() -> list:
        thresholds = AgentConfigAdaptater.get_value("unpaid_invoice_reminder_days", default=[7, 15, 30])
        if not isinstance(thresholds, list) or not thresholds:
            thresholds = [7, 15, 30]
        return sorted(int(t) for t in thresholds)

    @staticmethod
    def _write_reminder(client_name: str, invoice_ref: str, amount: float, days_late: int,
                        due_date: str, threshold: int) -> str:
        """Rédige le corps de la relance via le modèle léger (coût maîtrisé, §4.2/§5.6)."""
        openai_service = OpenaiService()
        if not openai_service.is_configured():
            return (
                f"Madame, Monsieur {client_name},\n\n"
                f"Nous vous rappelons que la facture {invoice_ref} d'un montant de "
                f"{amount:,.0f} FCFA, échue le {due_date}, reste impayée depuis {days_late} jours.\n"
                f"Nous vous remercions de bien vouloir procéder au règlement dans les meilleurs délais.\n\n"
                f"Cordialement,\nICT Consulting"
            )
        prompt = (
            f"Rédige une relance de paiement courtoise et professionnelle en français pour le client "
            f"'{client_name}' concernant la facture {invoice_ref} de {amount:,.0f} FCFA échue le {due_date} "
            f"(retard de {days_late} jours). Ton poli mais ferme. Pas de salutation ni signature, "
            f"juste le corps du message."
        )
        try:
            content, _, _ = openai_service.chat(
                messages=[{"role": "user", "content": prompt}], tools=None, tier="light", max_tokens=500
            )
            return content.strip()
        except Exception as e:
            logger.error(f"UnpaidInvoiceReminderUseCase._write_reminder failed: {e}")
            return (
                f"Madame, Monsieur {client_name},\n\n"
                f"Nous vous rappelons que la facture {invoice_ref} d'un montant de {amount:,.0f} FCFA, "
                f"échue le {due_date}, reste impayée depuis {days_late} jours.\n"
                f"Merci de procéder au règlement dans les meilleurs délais.\n\nCordialement,\nICT Consulting"
            )

    @staticmethod
    def execute(task=None) -> dict:
        try:
            thresholds = UnpaidInvoiceReminderUseCase._get_thresholds()
            sent_count = 0
            failures = []
            smtp_configured = SmtpService.is_configured()

            for i, threshold in enumerate(thresholds):
                # Fenêtre : jours de retard dans [threshold, suivant)
                next_threshold = thresholds[i + 1] if i + 1 < len(thresholds) else None
                invoices = InvoiceAdaptater.get_unpaid(min_days_late=threshold, limit=200)
                for invoice in invoices:
                    if next_threshold and invoice["days_late"] >= next_threshold:
                        continue  # sera relancée à l'échéance suivante
                    if not smtp_configured:
                        failures.append(f"{invoice['ref']}: SMTP non configuré")
                        continue

                    client_email = None
                    try:
                        client = ThirdpartyAdaptater.get_by_id(invoice["client_id"])
                        client_email = client.get("email")
                    except Exception as e:
                        logger.warning(f"Impossible de charger le client {invoice['client_id']}: {e}")

                    if not client_email:
                        failures.append(f"{invoice['ref']}: client sans e-mail")
                        continue

                    body = UnpaidInvoiceReminderUseCase._write_reminder(
                        client_name=invoice["client_name"],
                        invoice_ref=invoice["ref"],
                        amount=float(invoice["total_ttc"] or 0),
                        days_late=invoice["days_late"],
                        due_date=invoice["due_date"] or invoice["date"],
                        threshold=threshold,
                    )
                    subject = f"Relance {invoice['ref']} — paiement en attente"
                    sent = SmtpService.send(to=client_email, subject=subject, body=body)
                    if sent:
                        sent_count += 1
                        try:
                            AgendaEventAdaptater.create({
                                "label": f"Relance J+{threshold} facture {invoice['ref']}",
                                "type_code": "AC_ACT",
                                "thirdparty_id": invoice["client_id"],
                                "note": f"Relance e-mail envoyée à {client_email} — {subject}",
                            })
                        except Exception as e:
                            logger.warning(f"Échec journalisation agenda {invoice['ref']}: {e}")
                    AuditLogAdaptater.create(
                        action="relance_impaye",
                        target_type="invoice",
                        target_id=invoice["ref"],
                        details={"threshold": threshold, "days_late": invoice["days_late"],
                                 "amount": invoice["total_ttc"], "email": client_email, "sent": sent},
                        success=sent,
                    )

            summary = f"{sent_count} relance(s) envoyée(s)" + (f", {len(failures)} échec(s)" if failures else "")
            return {"summary": summary, "sent": sent_count, "failures": failures}
        except Exception as e:
            logger.error(f"UnpaidInvoiceReminderUseCase.execute failed: {e}")
            raise e


UseCase = UnpaidInvoiceReminderUseCase
