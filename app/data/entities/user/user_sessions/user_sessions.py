from datetime import datetime, timezone

from data.entities.config.entities_config import db


class UserSession(db.Model):
    """Session JWT active d'un utilisateur interne — utilisée pour la révocation de token (logout) et l'audit."""

    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_name = db.Column(db.String(255), nullable=True)
    device_ip = db.Column(db.String(255), nullable=True)
    token_jti = db.Column(db.String(255), unique=True, nullable=False)
    last_active = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = db.relationship("User", back_populates="sessions")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "device_name": self.device_name,
            "device_ip": self.device_ip,
            "revoked": self.revoked,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
