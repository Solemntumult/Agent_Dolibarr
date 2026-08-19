from datetime import datetime, timezone

from data.entities.config.entities_config import db


class AuditLog(db.Model):
    """Journal d'audit global — qui, quoi, quand, résultat (§5.5). Alimenté à chaque action
    sensible de l'agent (écriture Dolibarr, envoi d'e-mail, changement de configuration).
    """

    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # nullable : action automatique (ordonnanceur)
    tool_execution_id = db.Column(db.Integer, db.ForeignKey('tool_executions.id'), nullable=True)

    action = db.Column(db.String(100), nullable=False)  # ex. 'creer_facture', 'relance_impaye', 'login'
    target_type = db.Column(db.String(50), nullable=True)  # ex. 'invoice', 'thirdparty', 'user'
    target_id = db.Column(db.String(50), nullable=True)  # id Dolibarr ou id interne de la ressource visée
    details = db.Column(db.JSON, nullable=True)

    ip_address = db.Column(db.String(50), nullable=True)
    success = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tool_execution_id": self.tool_execution_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "success": self.success,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
