"""Gestionnaire de confirmation des actions d'écriture (cahier des charges §3.2, §5.1).

Toute écriture Dolibarr (ou envoi d'e-mail sortant) déclenchée par l'agent passe par
une ToolExecution au statut 'pending'. Seul un utilisateur interne habilité peut la
confirmer ou la rejeter depuis l'interface web (§4.4). Une fois confirmée, le
controller d'exécution vérifie le statut via @confirmation_required() avant l'écriture.
"""
from commons.enums.confirmation_status.confirmation_status import ConfirmationStatus
from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.tool_execution.tool_execution_adaptater import ToolExecutionAdaptater


class ConfirmationManager:

    @staticmethod
    def create_pending(tool_name: str, params: dict, conversation_id: int = None, user_id: int = None):
        """Enregistre une action d'écriture en attente de confirmation."""
        try:
            return ToolExecutionAdaptater.create_pending(
                tool_name=tool_name,
                tool_sense=ToolSense.WRITE,
                parameters=params,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        except Exception as e:
            logger.error(f"ConfirmationManager.create_pending failed: {e}")
            raise e

    @staticmethod
    def confirm(confirmation_id: int, user_id: int) -> bool:
        try:
            return ToolExecutionAdaptater.mark_confirmed(confirmation_id, user_id)
        except Exception as e:
            logger.error(f"ConfirmationManager.confirm failed: {e}")
            raise e

    @staticmethod
    def reject(confirmation_id: int, user_id: int = None) -> bool:
        try:
            tool_execution = ToolExecutionAdaptater.get_by_id(confirmation_id)
            if not tool_execution:
                return False
            tool_execution.confirmation_status = ConfirmationStatus.REJECTED
            tool_execution.success = False
            from data.entities.config.entities_config import db
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"ConfirmationManager.reject failed: {e}")
            return False

    @staticmethod
    def get(confirmation_id: int):
        return ToolExecutionAdaptater.get_by_id(confirmation_id)

    @staticmethod
    def list_pending(user_id: int = None) -> list:
        """Liste des écritures en attente de confirmation (pour l'utilisateur ou globales)."""
        from data.entities.tool_execution.tool_execution import ToolExecution
        try:
            query = ToolExecution.query.filter_by(
                confirmation_status=ConfirmationStatus.PENDING,
                tool_sense=ToolSense.WRITE,
            )
            if user_id:
                query = query.filter(
                    (ToolExecution.user_id == user_id) | (ToolExecution.user_id.is_(None))
                )
            return [te.to_dict() for te in query.order_by(ToolExecution.created_at.desc()).limit(50).all()]
        except Exception as e:
            logger.error(f"ConfirmationManager.list_pending failed: {e}")
            return []
