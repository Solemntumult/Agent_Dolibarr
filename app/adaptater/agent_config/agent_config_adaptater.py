"""Adaptateur configuration de l'agent — table clé/valeur AgentSettings (§4.4, §11).

Expose les paramètres modifiables par les administrateurs : échéances de relance
(J+7/J+15/J+30), seuil de stock, modèle par défaut, rapport hebdomadaire, etc.
"""
from commons.instances.instances import logger
from data.entities.config.entities_config import db
from data.entities.agent_settings.agent_settings import AgentSettings


class AgentConfigAdaptater:

    @staticmethod
    def get_all() -> list:
        try:
            return [s.to_dict() for s in AgentSettings.query.order_by(AgentSettings.key.asc()).all()]
        except Exception as e:
            logger.error(f"AgentConfigAdaptater.get_all failed: {e}")
            return []

    @staticmethod
    def get_value(key: str, default=None):
        try:
            setting = AgentSettings.query.filter_by(key=key).first()
            if not setting:
                return default
            return setting.value
        except Exception as e:
            logger.error(f"AgentConfigAdaptater.get_value({key}) failed: {e}")
            return default

    @staticmethod
    def set_value(key: str, value, description: str = None) -> bool:
        try:
            setting = AgentSettings.query.filter_by(key=key).first()
            if not setting:
                setting = AgentSettings(key=key, value=value, description=description)
                db.session.add(setting)
            else:
                setting.value = value
                if description:
                    setting.description = description
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"AgentConfigAdaptater.set_value({key}) failed: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def update_many(settings: dict) -> int:
        """Met à jour plusieurs paramètres à la fois (PUT /api/admin/agent_config/settings).
        Retourne le nombre de paramètres modifiés."""
        updated = 0
        for key, value in (settings or {}).items():
            if AgentConfigAdaptater.set_value(key, value):
                updated += 1
        return updated
