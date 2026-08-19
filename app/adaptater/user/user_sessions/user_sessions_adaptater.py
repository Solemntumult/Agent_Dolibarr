from commons.instances.instances import logger
from data.entities.config.entities_config import db
from data.entities.user.user_sessions.user_sessions import UserSession


class UserSessionsAdaptater:

    @staticmethod
    def create_session(user_id: int, token_jti: str, device_name: str = None, device_ip: str = None) -> UserSession:
        try:
            session = UserSession(
                user_id=user_id,
                token_jti=token_jti,
                device_name=device_name,
                device_ip=device_ip,
            )
            db.session.add(session)
            db.session.commit()
            return session
        except Exception as e:
            logger.error(f"Error creating user session: {e}")
            db.session.rollback()
            raise e

    @staticmethod
    def revoke_by_jti(token_jti: str) -> bool:
        try:
            session = UserSession.query.filter_by(token_jti=token_jti).first()
            if not session:
                return False
            session.revoked = True
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error revoking user session: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def is_revoked(token_jti: str) -> bool:
        session = UserSession.query.filter_by(token_jti=token_jti).first()
        return bool(session and session.revoked)
