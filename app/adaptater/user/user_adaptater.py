from commons.instances.instances import logger
from data.entities.config.entities_config import db
from data.entities.user.user import User


class UserAdaptater:

    @staticmethod
    def get_user_by_email(email: str):
        if not email:
            return None
        return User.query.filter_by(email=email, is_deleted=False).first()

    @staticmethod
    def get_user_by_id(user_id: int):
        if not user_id:
            return None
        return User.query.filter_by(id=user_id, is_deleted=False).first()

    @staticmethod
    def register_login(user: User):
        try:
            from datetime import datetime, timezone
            user.login_count = (user.login_count or 0) + 1
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
        except Exception as e:
            logger.error(f"Error registering login: {e}")
            db.session.rollback()
