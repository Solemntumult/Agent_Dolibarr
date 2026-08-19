from sqlalchemy import exists

from commons.enums.user_roles.roles import UserRole
from commons.instances.instances import logger
from data.entities.config.entities_config import db
from data.entities.user.user import User


class SuperAdminSeeder:
    """Crée le premier compte administrateur interne s'il n'en existe aucun.

    Nécessaire car il n'existe pas de route d'inscription publique côté agent
    (§1.3 : réservé aux utilisateurs internes) — il faut donc un compte initial
    pour pouvoir se connecter et créer les autres comptes internes via /api/admin.
    """

    @staticmethod
    def check_existing_admin() -> bool:
        try:
            return db.session.query(
                exists().where(User.role == UserRole.ADMIN.value, User.is_deleted == False)  # noqa: E712
            ).scalar()
        except Exception as e:
            logger.error(f"Error checking existing admin: {e}")
            raise e

    @staticmethod
    def create_admin() -> User:
        from commons.config.config import Config

        try:
            if not Config.ADMIN_EMAIL or not Config.ADMIN_PASSWORD:
                logger.warning(
                    "ADMIN_EMAIL / ADMIN_PASSWORD non définis dans l'environnement : "
                    "aucun administrateur initial créé."
                )
                return None

            admin = User(
                full_name=Config.ADMIN_FULL_NAME or "Administrateur ICT Consulting",
                email=Config.ADMIN_EMAIL,
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            admin.set_password(Config.ADMIN_PASSWORD)

            db.session.add(admin)
            db.session.commit()
            logger.info(f"Administrateur initial créé : {admin.email}")
            return admin
        except Exception as e:
            logger.error(f"Error creating initial admin: {e}")
            db.session.rollback()
            raise e

    @staticmethod
    def run():
        if not SuperAdminSeeder.check_existing_admin():
            SuperAdminSeeder.create_admin()
        else:
            logger.info("Un administrateur interne existe déjà, seeder ignoré.")
