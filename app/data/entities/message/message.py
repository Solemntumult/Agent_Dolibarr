from datetime import datetime, timezone

from data.entities.config.entities_config import db


class Message(db.Model):
    """Message individuel d'une conversation (utilisateur, agent, ou outil)."""

    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' | 'assistant' | 'tool'
    content = db.Column(db.Text, nullable=False)
    model_tier_used = db.Column(db.String(20), nullable=True)  # cf. commons/enums/model_tier — traçabilité coût §5.6
    tokens_input = db.Column(db.Integer, nullable=True)
    tokens_output = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    conversation = db.relationship("Conversation", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "model_tier_used": self.model_tier_used,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
