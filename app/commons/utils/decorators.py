from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt, get_jwt_identity

from commons.enums.user_roles.roles import UserRole
from commons.helpers.custom_response import CustomResponse
from commons.instances.instances import logger


def internal_user_required():
    """Vérifie que le porteur du token est un utilisateur interne actif et non révoqué.

    Répond à l'exigence du cahier des charges §5.1 : "Authentification de l'application
    web ; aucun accès anonyme." Doit être utilisé après @jwt_required().
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from adaptater.user.user_adaptater import UserAdaptater
            from adaptater.user.user_sessions.user_sessions_adaptater import UserSessionsAdaptater

            try:
                jti = get_jwt().get('jti')
                if UserSessionsAdaptater.is_revoked(jti):
                    return CustomResponse.send_response(
                        message="Session expirée ou révoquée, veuillez vous reconnecter.",
                        success=False, status_code=401
                    )

                user_id = get_jwt_identity()
                user = UserAdaptater.get_user_by_id(int(user_id))
                if not user or not user.is_active:
                    return CustomResponse.send_response(
                        message="Utilisateur interne introuvable ou désactivé.",
                        success=False, status_code=403
                    )
                g.current_user = user
                return fn(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in internal_user_required: {e}")
                return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)
        return wrapper
    return decorator


def admin_required():
    """Réserve la route aux utilisateurs internes ayant le rôle ADMIN (ex. §4.4 configuration de l'agent)."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user or user.role != UserRole.ADMIN.value:
                return CustomResponse.send_response(
                    message="Accès réservé aux administrateurs.", success=False, status_code=403
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def confirmation_required():
    """Vérifie qu'une confirmation utilisateur validée existe avant toute écriture Dolibarr.

    Répond à l'exigence du cahier des charges §3.2/§5.1 : toute création ou modification
    de document Dolibarr est soumise à confirmation avant écriture définitive.
    Le controller d'écriture doit fournir un confirmation_id dans le corps de la requête ;
    ce décorateur vérifie son statut auprès d'AgentConfirmationAdaptater avant d'exécuter l'outil.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask import request
            from commons.enums.confirmation_status.confirmation_status import ConfirmationStatus
            from adaptater.tool_execution.tool_execution_adaptater import ToolExecutionAdaptater

            data = request.get_json(silent=True) or {}
            confirmation_id = data.get('confirmation_id')
            if not confirmation_id:
                return CustomResponse.send_response(
                    message="confirmation_id requis pour toute action d'écriture.",
                    success=False, status_code=422
                )
            tool_execution = ToolExecutionAdaptater.get_by_id(confirmation_id)
            if not tool_execution or tool_execution.confirmation_status != ConfirmationStatus.CONFIRMED:
                return CustomResponse.send_response(
                    message="Aucune confirmation validée pour cette action.",
                    success=False, status_code=403
                )
            g.tool_execution = tool_execution
            return fn(*args, **kwargs)
        return wrapper
    return decorator
