from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from commons.enums.user_roles.roles import UserRole
from data.entities.config.entities_config import db


class User(db.Model):
    """Utilisateur interne ICT Consulting autorisé à utiliser l'agent (cahier des charges §5.1 : aucun accès anonyme)."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False, default=UserRole.USER.value)

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    login_count = db.Column(db.Integer, default=0, nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    sessions = db.relationship("UserSession", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, raw_password: str):
        self.password = generate_password_hash(raw_password, method='pbkdf2:sha256')

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password, raw_password)

    def from_dict(self, data: dict):
        self.full_name = data.get('full_name')
        self.email = data.get('email')
        self.role = data.get('role', UserRole.USER.value)
        if data.get('password'):
            self.set_password(data.get('password'))
        return self

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
