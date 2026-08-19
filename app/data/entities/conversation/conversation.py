from datetime import datetime, timezone

from data.entities.config.entities_config import db


class Conversation(db.Model):
    """Fil de discussion entre un utilisateur interne et l'agent (canal web ou e-mail)."""

    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # nullable : conversation issue du canal e-mail
    channel = db.Column(db.String(20), nullable=False, default='web')  # 'web' | 'email'
    title = db.Column(db.String(255), nullable=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    messages = db.relationship("Message", back_populates="conversation", lazy="dynamic", cascade="all, delete-orphan")
    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "channel": self.channel,
            "title": self.title,
            "is_archived": self.is_archived,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
