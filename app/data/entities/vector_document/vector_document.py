from datetime import datetime, timezone

from data.entities.config.entities_config import db


class VectorDocument(db.Model):
    """Document indexé pour la recherche sémantique (clients, produits Dolibarr)."""

    __tablename__ = "vector_documents"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(32), nullable=False, index=True)  # client | product
    entity_id = db.Column(db.Integer, nullable=False)
    content_text = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.JSON, nullable=False)  # liste de floats
    metadata_json = db.Column(db.JSON, nullable=True)

    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint("entity_type", "entity_id", name="uq_vector_entity"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "content_text": self.content_text,
            "metadata": self.metadata_json or {},
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
