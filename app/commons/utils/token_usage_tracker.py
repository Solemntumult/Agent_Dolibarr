"""Suivi de la consommation de jetons OpenAI (cahier des charges §5.6).

Les compteurs sont persistés sur le message assistant associé (champs
tokens_input / tokens_output / model_tier_used de la table messages) et
journalisés en log pour piloter le coût de l'API.
"""
from commons.instances.instances import logger


class TokenUsageTracker:

    @staticmethod
    def record(model_name: str, input_tokens: int, output_tokens: int, message_id: int = None):
        try:
            if message_id:
                from data.entities.config.entities_config import db
                from data.entities.message.message import Message
                message = Message.query.filter_by(id=message_id).first()
                if message:
                    message.tokens_input = int(input_tokens or 0)
                    message.tokens_output = int(output_tokens or 0)
                    message.model_tier_used = model_name
                    db.session.commit()
            logger.info(f"Tokens used - model={model_name} in={input_tokens} out={output_tokens}")
        except Exception as e:
            logger.error(f"Error in TokenUsageTracker.record: {e}")
            raise e
