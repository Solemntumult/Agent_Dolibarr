from enum import Enum


class UserRole(Enum):
    """Rôles des utilisateurs internes autorisés à utiliser l'agent (cahier des charges §1.3, §5.1)."""

    ADMIN = "admin"   # Accès complet : configuration de l'agent, gestion des utilisateurs internes
    USER = "user"     # Accès conversationnel + écriture avec confirmation, pas d'accès à la configuration

    @staticmethod
    def all_roles():
        return [role.value for role in UserRole]
