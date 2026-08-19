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
            return CustomResponse.send_response(
                message="OK", success=True, status_code=200,
                data={
                    "imap_configured": ImapService.is_configured(),
                    "smtp_configured": SmtpService.is_configured(),
                    "allowed_senders": Config.ALLOWED_EMAIL_SENDERS,
                    "report_recipients": Config.REPORT_RECIPIENTS,
                },
            )
        except Exception as e:
            logger.error(f"Error in EmailController.status: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def poll():
        """POST /api/email/poll — déclenche manuellement le traitement de la boîte entrante (U6)."""
        try:
            result = IncomingEmailUseCase.execute()
            return CustomResponse.send_response(
                message="Traitement terminé.", success=True, status_code=200, data=result
            )
        except Exception as e:
            logger.error(f"Error in EmailController.poll: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)
