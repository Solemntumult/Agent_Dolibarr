from commons.instances.instances import logger
from data.entities.agent_settings.agent_settings import AgentSettings
from data.entities.config.entities_config import db

# Valeurs par défaut issues du cahier des charges (§3.3 relances, §4.2 choix du modèle)
DEFAULT_SETTINGS = [
    {
        "key": "unpaid_invoice_reminder_days",
        "value": [7, 15, 30],
        "description": "Échéances (en jours de retard) déclenchant une relance automatique des factures impayées.",
    },
    {
        "key": "stock_alert_threshold",
        "value": 5,
        "description": "Seuil de stock (par défaut, en l'absence de seuil produit spécifique) déclenchant une alerte.",
    },
    {
        "key": "model_tier_default",
        "value": "balanced",
        "description": "Modèle par défaut pour l'agent conversationnel principal (light | balanced | advanced).",
    },
    {
        "key": "weekly_report_enabled",
        "value": True,
        "description": "Active l'envoi du rapport hebdomadaire d'activité par courriel.",
    },
    {
        "key": "vector_search_enabled",
        "value": True,
        "description": "Active la recherche sémantique vectorielle (clients, produits).",
    },
    {
        "key": "llm_history_limit",
        "value": 6,
        "description": "Nombre de messages récents envoyés au modèle (optimisation tokens).",
    },
]


class AgentSettingsSeeder:

    @staticmethod
    def run():
        try:
            for default in DEFAULT_SETTINGS:
                existing = AgentSettings.query.filter_by(key=default["key"]).first()
                if not existing:
                    db.session.add(AgentSettings(**default))
            db.session.commit()
            logger.info("Configuration par défaut de l'agent vérifiée/initialisée.")
        except Exception as e:
            logger.error(f"Error seeding agent settings: {e}")
            db.session.rollback()
            raise e
