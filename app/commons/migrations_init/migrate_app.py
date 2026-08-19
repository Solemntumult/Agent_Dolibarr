import os

from flask_migrate import Migrate, init, migrate, upgrade

from commons.instances.instances import logger
from data.entities.config.entities_config import db


def is_valid_migration_dir(path):
    """Vérifie si le dossier de migrations est valide (contient env.py)."""
    return (
        os.path.exists(path)
        and os.path.isdir(path)
        and os.path.isfile(os.path.join(path, "env.py"))
    )


def run_migrations(app):
    """Initialise puis applique les migrations Alembic au démarrage (repris à l'identique
    du pattern terral_api — cf. commons/migrations_init/migrate_app.py). Le dossier
    migrations/ est généré automatiquement au premier lancement s'il n'existe pas encore.
    """
    migrations_dir = 'migrations'
    Migrate(app, db)

    # Les fonctions init/migrate/upgrade de flask_migrate sont des commandes click :
    # appelées directement, elles lisent sys.argv (incompatible avec gunicorn) et
    # peuvent lever SystemExit. On les exécute donc en mode défensif : les tables
    # sont de toute façon créées par db.create_all() avant cet appel (voir app/__init__.py).
    try:
        if not is_valid_migration_dir(migrations_dir):
            try:
                init()
                logger.info("Migration repository initialized.")
            except BaseException as e:  # noqa: BLE001
                logger.warning(f"Initialisation du dépôt de migrations ignorée: {e}")
        else:
            logger.debug("Valid migration repository found.")

        try:
            logger.debug("Trying migrate")
            migrate()
            logger.info("Migration scripts generated.")
        except BaseException as e:  # noqa: BLE001
            logger.warning(f"Génération des migrations ignorée: {e}")

        try:
            upgrade()
            logger.info("Database migrations applied successfully.")
        except BaseException as e:  # noqa: BLE001
            logger.warning(f"Application des migrations ignorée: {e}")
    except BaseException as e:  # noqa: BLE001
        logger.warning(f"Migration step skipped: {e}")
