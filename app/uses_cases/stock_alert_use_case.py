"""Use case : alerte de stock (cahier des charges §3.3, U4).

Détecte les produits dont le stock est passé sous le seuil configuré et notifie
les destinataires (REPORT_RECIPIENTS ou administrateur) par courriel.
"""
from commons.config.config import Config
from commons.instances.instances import logger
from adaptater.audit.audit_log_adaptater import AuditLogAdaptater
from adaptater.dolibarr.product_adaptater import ProductAdaptater
from services.email.smtp_service import SmtpService


class StockAlertUseCase:

    @staticmethod
    def _recipients() -> list:
        recipients = Config.REPORT_RECIPIENTS or []
        if not recipients and Config.ADMIN_EMAIL:
            recipients = [Config.ADMIN_EMAIL]
        return recipients

    @staticmethod
    def execute(task=None) -> dict:
        try:
            stock_report = ProductAdaptater.get_stock_level()
            below = stock_report.get("below_threshold", [])

            if not below:
                AuditLogAdaptater.create(
                    action="alerte_stock", target_type="product",
                    details={"threshold": stock_report.get("threshold"), "alerts": 0},
                    success=True,
                )
                return {"summary": "Aucun produit sous le seuil de stock", "alerts": 0}

            recipients = StockAlertUseCase._recipients()
            lines = "\n".join(
                f"- {p['label']} (réf. {p['ref']}): {p['stock']} en stock"
                for p in below
            )
            body = (
                f"Bonjour,\n\nLes produits suivants sont passés sous le seuil d'alerte de stock "
                f"({stock_report.get('threshold')} unités) :\n\n{lines}\n\n"
                f"Cordialement,\nAgent IA ICT Consulting"
            )

            sent = False
            if recipients:
                sent = SmtpService.send(
                    to=", ".join(recipients),
                    subject=f"Alerte stock — {len(below)} produit(s) sous le seuil",
                    body=body,
                )
            else:
                logger.warning("Aucun destinataire configuré pour l'alerte de stock.")

            AuditLogAdaptater.create(
                action="alerte_stock",
                target_type="product",
                details={"threshold": stock_report.get("threshold"),
                         "products": [p["ref"] for p in below], "recipients": recipients, "sent": sent},
                success=sent,
            )
            return {"summary": f"Alerte envoyée pour {len(below)} produit(s)", "alerts": len(below), "sent": sent}
        except Exception as e:
            logger.error(f"StockAlertUseCase.execute failed: {e}")
            raise e


UseCase = StockAlertUseCase
