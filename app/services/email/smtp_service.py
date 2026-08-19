"""Service SMTP — envoi des relances, réponses, notifications et rapports (§4.5).

Tout e-mail sortant est soumis à la politique de confirmation de l'application
(§5.1) ; les tâches planifiées suivent une politique prédéfinie (validée à la
configuration de la tâche).
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from commons.config.config import Config
from commons.instances.instances import logger


class SmtpService:

    @staticmethod
    def is_configured() -> bool:
        return bool(Config.SMTP_HOST and Config.SMTP_USER and Config.SMTP_PASSWORD)

    @staticmethod
    def send(to: str, subject: str, body: str, body_html: str = None) -> bool:
        """Envoie un e-mail texte (et/ou HTML) à un destinataire."""
        if not SmtpService.is_configured():
            logger.warning("SMTP non configuré — envoi ignoré.")
            return False
        try:
            message = MIMEMultipart("alternative")
            message["From"] = Config.SMTP_FROM
            message["To"] = to
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain", "utf-8"))
            if body_html:
                message.attach(MIMEText(body_html, "html", "utf-8"))

            if Config.SMTP_USE_SSL:
                server = smtplib.SMTP_SSL(Config.SMTP_HOST, timeout=30)
            else:
                server = smtplib.SMTP(Config.SMTP_HOST, timeout=30)
                server.starttls()
            try:
                server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.sendmail(Config.SMTP_FROM, [to], message.as_string())
            finally:
                server.quit()
            logger.info(f"E-mail envoyé à {to} — sujet: {subject}")
            return True
        except Exception as e:
            logger.error(f"SmtpService.send failed: {e}")
            return False
