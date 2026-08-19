"""Adaptateur journal d'audit — traçabilité qui/quoi/quand/résultat (§5.5).

Alimenté à chaque action sensible de l'agent : écriture Dolibarr, envoi d'e-mail,
changement de configuration, tâches planifiées (user_id nullable = action automatique).
"""
from commons.instances.instances import logger
from data.entities.config.entities_config import db
from data.entities.audit_log.audit_log import AuditLog


class AuditLogAdaptater:

    @staticmethod
    def create(action: str, target_type: str = None, target_id: str = None,
               details: dict = None, user_id: int = None, ip_address: str = None,
               success: bool = True, tool_execution_id: int = None) -> AuditLog:
        try:
            log_entry = AuditLog(
                user_id=user_id,
                tool_execution_id=tool_execution_id,
                action=action,
                target_type=target_type,
                target_id=str(target_id) if target_id is not None else None,
                details=details,
                ip_address=ip_address,
                success=success,
            )
            db.session.add(log_entry)
            db.session.commit()
            return log_entry
        except Exception as e:
            logger.error(f"AuditLogAdaptater.create failed: {e}")
            db.session.rollback()
            raise e

    @staticmethod
    def list(limit: int = 100, action: str = None, user_id: int = None) -> list:
        try:
            query = AuditLog.query
            if action:
                query = query.filter(AuditLog.action == action)
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            logs = query.order_by(AuditLog.created_at.desc()).limit(min(int(limit) or 100, 500)).all()
            return [log.to_dict() for log in logs]
        except Exception as e:
            logger.error(f"AuditLogAdaptater.list failed: {e}")
            return []
