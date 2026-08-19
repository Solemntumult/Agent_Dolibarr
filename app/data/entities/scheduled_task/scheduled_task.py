from datetime import datetime, timezone

from data.entities.config.entities_config import db


class ScheduledTask(db.Model):
    """Tâche planifiée exécutée par l'ordonnanceur (§3.3, §4.6) : relances d'impayés,
    alertes de stock, rapports périodiques.
    """

    __tablename__ = 'scheduled_tasks'

    id = db.Column(db.Integer, primary_key=True)
    task_type = db.Column(db.String(50), nullable=False)  # 'unpaid_reminder' | 'stock_alert' | 'periodic_report'
    cron_expression = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    config = db.Column(db.JSON, nullable=True)  # ex. seuils J+7/J+15/J+30, seuil de stock, destinataires

    last_run_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_run_success = db.Column(db.Boolean, nullable=True)
    last_run_summary = db.Column(db.Text, nullable=True)

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
            "task_type": self.task_type,
            "cron_expression": self.cron_expression,
            "is_active": self.is_active,
            "config": self.config,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_success": self.last_run_success,
            "last_run_summary": self.last_run_summary,
        }
