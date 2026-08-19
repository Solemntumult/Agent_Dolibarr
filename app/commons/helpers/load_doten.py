import os
from dotenv import load_dotenv
from commons.instances.instances import logger

ENV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "const", "const", ".env"
)


def load_env():
    try:
        load_dotenv(dotenv_path=ENV_PATH)
        logger.info(f"Variables d'environnement chargées depuis {ENV_PATH}")
    except Exception as e:
        logger.error(f"Erreur lors du chargement du .env: {e}")
        raise e
