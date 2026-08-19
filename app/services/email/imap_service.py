"""Service IMAP — lecture de la boîte e-mail dédiée de l'agent (§4.5).

La liste d'expéditeurs autorisés (ALLOWED_EMAIL_SENDERS) et le garde-fou anti
injection (PromptGuardService) sont appliqués par le use case e-mail entrant.
"""
import email
import imaplib
from email.header import decode_header, make_header

from commons.config.config import Config
from commons.instances.instances import logger


class ImapService:

    @staticmethod
    def is_configured() -> bool:
        return bool(Config.IMAP_HOST and Config.IMAP_USER and Config.IMAP_PASSWORD)

    @staticmethod
    def _decode(value) -> str:
        if not value:
            return ""
        try:
            return str(make_header(decode_header(value)))
        except Exception:
            return str(value)

    @staticmethod
    def _get_body(message) -> str:
        """Extrait le corps texte d'un e-mail (multipart inclus)."""
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition") or "")
                if content_type == "text/plain" and "attachment" not in disposition:
                    try:
                        return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                    except Exception:
                        continue
            return ""
        try:
            return message.get_payload(decode=True).decode(message.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            return str(message.get_payload())

    @staticmethod
    def fetch_unseen(limit: int = 20) -> list:
        """Récupère les e-mails non lus. Retourne [{uid, from_, subject, body, date}]."""
        if not ImapService.is_configured():
            logger.warning("IMAP non configuré — lecture de la boîte ignorée.")
            return []
        try:
            if Config.IMAP_USE_SSL:
                mail = imaplib.IMAP4_SSL(Config.IMAP_HOST)
            else:
                mail = imaplib.IMAP4(Config.IMAP_HOST)
            try:
                mail.login(Config.IMAP_USER, Config.IMAP_PASSWORD)
                mail.select("INBOX")
                status, data = mail.search(None, "UNSEEN")
                uids = data[0].split() if status == "OK" else []
                results = []
                for uid in uids[-int(limit):]:
                    status, msg_data = mail.fetch(uid, "(RFC822)")
                    if status != "OK" or not msg_data or not msg_data[0]:
                        continue
                    message = email.message_from_bytes(msg_data[0][1])
                    results.append({
                        "uid": int(uid),
                        "from_": ImapService._decode(message.get("From")),
                        "subject": ImapService._decode(message.get("Subject")),
                        "body": ImapService._get_body(message),
                        "date": str(message.get("Date") or ""),
                    })
                return results
            finally:
                try:
                    mail.logout()
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"ImapService.fetch_unseen failed: {e}")
            return []

    @staticmethod
    def mark_seen(uid: int) -> bool:
        """Marque un e-mail comme lu après traitement."""
        if not ImapService.is_configured():
            return False
        try:
            if Config.IMAP_USE_SSL:
                mail = imaplib.IMAP4_SSL(Config.IMAP_HOST)
            else:
                mail = imaplib.IMAP4(Config.IMAP_HOST)
            try:
                mail.login(Config.IMAP_USER, Config.IMAP_PASSWORD)
                mail.select("INBOX")
                mail.store(str(uid), "+FLAGS", "\\Seen")
                return True
            finally:
                try:
                    mail.logout()
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"ImapService.mark_seen failed: {e}")
            return False
