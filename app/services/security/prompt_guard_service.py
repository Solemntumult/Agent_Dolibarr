"""Garde-fou contre les injections d'instructions (cahier des charges §4.5, §5.1).

Les contenus provenant de courriels ou de données Dolibarr sont traités comme des
DONNÉES, jamais comme des ordres. Ce service détecte les tentatives d'injection
(classiques) et neutralise le texte avant tout passage au LLM. Les écritures ne
peuvent de toute façon être déclenchées que par un utilisateur autorisé ou une
tâche planifiée validée.
"""
import re

import email.utils

from commons.config.config import Config
from commons.instances.instances import logger

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)?\s*(instructions|prompts|rules)",
    r"oublie\s+(tes|les)\s+(instructions|règles|prompts|consignes)",
    r"(tu es|vous êtes|act as|pretend to be)\s+.*(system|admin|root)",
    r"disregard\s+(all\s+)?(instructions|previous)",
    r"(ne\s+suis|don't\s+follow|do not\s+follow)\s+.*(instructions|consignes)",
    r"(system\s*prompt|prompt\s*injection)",
    r"reveal\s+(your\s+)?(system|prompt|instructions|api|keys?|password)",
    r"divulgue\s+(tes|vos)\s+(instructions|clés|mots\s+de\s+passe|prompt)",
    r"<(system|assistant|user)[^>]*>",
]

_MAX_BODY_LENGTH = 4000


class PromptGuardService:

    @staticmethod
    def is_sender_allowed(from_header: str) -> bool:
        """Vérifie que l'expéditeur fait partie de la liste autorisée (§4.5)."""
        if not Config.ALLOWED_EMAIL_SENDERS:
            logger.warning("Aucun expéditeur autorisé configuré — e-mails entrants ignorés.")
            return False
        name, address = email.utils.parseaddr(from_header or "")
        sender = (address or from_header or "").strip().lower()
        return any(sender == allowed or sender.endswith("@" + allowed.lstrip("@"))
                   for allowed in Config.ALLOWED_EMAIL_SENDERS)

    @staticmethod
    def sanitize(text: str) -> str:
        """Neutralise le contenu : tronque, supprime les blocs d'injection détectés."""
        if not text:
            return ""
        text = text[: _MAX_BODY_LENGTH]
        for pattern in _INJECTION_PATTERNS:
            text = re.sub(pattern, "[contenu neutralisé]", text, flags=re.IGNORECASE)
        # Retire les balises résiduelles
        text = re.sub(r"<[^>]+>", " ", text)
        return text.strip()

    @staticmethod
    def contains_injection(text: str) -> bool:
        """True si le texte contient une tentative d'injection connue."""
        if not text:
            return False
        for pattern in _INJECTION_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True
        return False

    @staticmethod
    def guard(content: str, sender: str = None) -> dict:
        """Point d'entrée unique : vérifie expéditeur + injection et retourne un contenu sûr.

        Retourne {"allowed": bool, "suspicious": bool, "safe_body": str, "reason": str}.
        """
        if sender and not PromptGuardService.is_sender_allowed(sender):
            return {"allowed": False, "suspicious": False, "safe_body": "",
                    "reason": "Expéditeur non autorisé."}
        safe_body = PromptGuardService.sanitize(content)
        if PromptGuardService.contains_injection(content):
            return {"allowed": True, "suspicious": True, "safe_body": safe_body,
                    "reason": "Tentative d'injection détectée — contenu traité comme donnée."}
        return {"allowed": True, "suspicious": False, "safe_body": safe_body, "reason": ""}
