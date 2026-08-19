"""Use case : rapport périodique (cahier des charges §3.4, U5).

Produit une synthèse commerciale (CA, évolution, meilleurs clients, impayés) à
partir des données Dolibarr, la fait rédiger par le modèle, puis l'envoie par
courriel aux destinataires configurés.
"""
from commons.config.config import Config
from commons.instances.instances import logger
from adaptater.audit.audit_log_adaptater import AuditLogAdaptater
from adaptater.dolibarr.invoice_adaptater import InvoiceAdaptater
from services.email.smtp_service import SmtpService
from services.openai.openai_service import OpenaiService


class PeriodicReportUseCase:

    @staticmethod
    def _recipients() -> list:
        recipients = Config.REPORT_RECIPIENTS or []
        if not recipients and Config.ADMIN_EMAIL:
            recipients = [Config.ADMIN_EMAIL]
        return recipients

    @staticmethod
    def _collect_data() -> dict:
        stats = InvoiceAdaptater.get_sales_statistics(period="mois")
        unpaid = InvoiceAdaptater.get_unpaid(min_days_late=0, limit=50)
        unpaid_total = round(sum(float(i["total_ttc"] or 0) for i in unpaid), 2)
        return {
            "ca_mois": stats["current_period"],
            "evolution_pct": stats["evolution_pct"],
            "top_clients": stats["current_period"]["top_clients"],
            "nb_factures": stats["current_period"]["count"],
            "impayes": {"count": len(unpaid), "total_ttc": unpaid_total},
        }

    @staticmethod
    def _write_report(data: dict) -> str:
        openai_service = OpenaiService()
        if not openai_service.is_configured():
            return (
                f"Rapport d'activité : CA du mois {data['ca_mois']['total_ttc']:,.0f} FCFA "
                f"({data['nb_factures']} factures), évolution {data['evolution_pct']}% vs période "
                f"précédente, {data['impayes']['count']} facture(s) impayée(s) pour "
                f"{data['impayes']['total_ttc']:,.0f} FCFA."
            )
        prompt = (
            "Rédige en français un rapport d'activité hebdomadaire court et professionnel à partir de "
            f"ces données : {data}. Structure : 1) Chiffre d'affaires, 2) Évolution, 3) Meilleurs clients, "
            "4) Impayés. Pas d'emoji. "
        )
        try:
            content, _, _ = openai_service.chat(
                messages=[{"role": "user", "content": prompt}], tools=None, tier="balanced", max_tokens=800
            )
            return content.strip()
        except Exception as e:
            logger.error(f"PeriodicReportUseCase._write_report failed: {e}")
            raise e

    @staticmethod
    def execute(task=None) -> dict:
        try:
            data = PeriodicReportUseCase._collect_data()
            report = PeriodicReportUseCase._write_report(data)
            recipients = PeriodicReportUseCase._recipients()

            sent = False
            if recipients:
                sent = SmtpService.send(
                    to=", ".join(recipients),
                    subject="Rapport d'activité hebdomadaire",
                    body=report,
                )
            else:
                logger.warning("Aucun destinataire configuré pour le rapport périodique.")

            AuditLogAdaptater.create(
                action="rapport_periodique",
                target_type="report",
                details={"recipients": recipients, "sent": sent, "data": data},
                success=sent,
            )
            return {"summary": f"Rapport envoyé ({'oui' if sent else 'non'})", "sent": sent}
        except Exception as e:
            logger.error(f"PeriodicReportUseCase.execute failed: {e}")
            raise e


UseCase = PeriodicReportUseCase
