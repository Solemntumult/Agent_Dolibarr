# Créer l'application Flask
import os
import sys

# S'assurer que le dossier app est dans sys.path pour les imports relatifs/absolus
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask_migrate import Migrate
from commons.config.config import Config
from commons.instances.instances import logger
from seeder.seeder_all import SeederAll
from core.dependance.dependance import create_app
from data.entities.config.entities_config import db
from commons.migrations_init.migrate_app import run_migrations

# Import explicite de toutes les entités : nécessaire pour que db.create_all() et les
# migrations Alembic détectent chaque table, même tant que les routes métier (chat,
# confirmation, email) ne sont encore que des squelettes et n'importent pas ces
# entités transitivement.
from data.entities.user.user import User  # noqa: F401
from data.entities.user.user_sessions.user_sessions import UserSession  # noqa: F401
from data.entities.conversation.conversation import Conversation  # noqa: F401
from data.entities.message.message import Message  # noqa: F401
from data.entities.tool_execution.tool_execution import ToolExecution  # noqa: F401
from data.entities.audit_log.audit_log import AuditLog  # noqa: F401
from data.entities.scheduled_task.scheduled_task import ScheduledTask  # noqa: F401
from data.entities.agent_settings.agent_settings import AgentSettings  # noqa: F401
from data.entities.vector_document.vector_document import VectorDocument  # noqa: F401
from data.entities.email.inbound_email import InboundEmail  # noqa: F401

app = create_app()

db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()
    run_migrations(app)

    SeederAll.run_all()

    if Config.VECTOR_SYNC_ON_STARTUP and Config.VECTOR_SEARCH_ENABLED:
        try:
            from services.vector.dolibarr_vector_sync_service import DolibarrVectorSyncService
            sync_result = DolibarrVectorSyncService.sync_all()
            logger.info(f"Sync vectoriel au démarrage : {sync_result.get('summary')}")
        except Exception as sync_err:
            logger.warning(f"Sync vectoriel au démarrage ignorée : {sync_err}")

# Démarrage de l'ordonnanceur (cahier des charges §3.3/§4.6). En mode debug, le
# reloader Flask exécute ce module deux fois : on ne démarre l'ordonnanceur que
# dans le processus enfant (WERKZEUG_RUN_MAIN=true).
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    from services.scheduler.scheduler_service import SchedulerService
    SchedulerService.start(app)

if __name__ == "__main__":
    # Lancer l'application (port configurable via PORT — ex. 5000 par défaut).
    # debug/reloader uniquement en développement (FLASK_DEBUG=1) : en usage normal le
    # reloader redémarre le serveur à chaque changement de fichier et coupe les requêtes
    # en cours, ce qui bloquait le chat (réponse coupée, saisie gelée).
    debug_mode = os.getenv("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", "5000")), debug=debug_mode)
