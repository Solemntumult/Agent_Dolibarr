from datetime import datetime, timezone

from data.entities.config.entities_config import db


class ToolExecution(db.Model):
    """Trace chaque appel d'outil déclenché par l'agent — cœur de la traçabilité (§5.5) et du
    mécanisme de confirmation avant écriture (§3.2, §5.1). Une ligne d'écriture (tool_sense='write')
    reste au statut 'pending' tant qu'aucun utilisateur habilité ne l'a confirmée.
    """

    __tablename__ = 'tool_executions'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    tool_name = db.Column(db.String(100), nullable=False)
    tool_sense = db.Column(db.String(10), nullable=False)  # cf. commons/enums/tool_sense : 'read' | 'write'
    parameters = db.Column(db.JSON, nullable=True)
    result = db.Column(db.JSON, nullable=True)

    confirmation_status = db.Column(db.String(20), nullable=False, default='pending')  # cf. commons/enums/confirmation_status
    confirmed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    success = db.Column(db.Boolean, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

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
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "tool_name": self.tool_name,
            "tool_sense": self.tool_sense,
            "parameters": self.parameters,
            "result": self.result,
            "confirmation_status": self.confirmation_status,
            "confirmed_by_user_id": self.confirmed_by_user_id,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
