from flask_jwt_extended import create_access_token

from commons.instances.instances import logger
from data.entities.config.entities_config import db
from data.entities.user.user import User


class AuthAdaptater:

    @staticmethod
    def create_user(data: dict) -> User:
        try:
            user = User()
            user = user.from_dict(data=data)
            db.session.add(user)
            db.session.commit()
            return user
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.session.rollback()
            raise e

    @staticmethod
    def verify_password(user: User, password: str) -> bool:
        try:
            return user.check_password(password)
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    @staticmethod
    def create_token(user: User) -> str:
        try:
            additional_claims = {"role": user.role}
            return create_access_token(identity=str(user.id), additional_claims=additional_claims)
        except Exception as e:
            logger.error(f"Error creating token: {e}")
            raise e
