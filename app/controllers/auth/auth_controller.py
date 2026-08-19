from flask import request
from flask_jwt_extended import decode_token, get_jwt, get_jwt_identity

from adaptater.auth.auth_adaptater import AuthAdaptater
from adaptater.user.user_adaptater import UserAdaptater
from adaptater.user.user_sessions.user_sessions_adaptater import UserSessionsAdaptater
from commons.helpers.custom_response import CustomResponse
from commons.instances.instances import logger
from data.entities.user.user import User


class AuthController:

    @staticmethod
    def login():
        try:
            data = request.get_json() or {}
            email = (data.get('email') or '').strip()
            password = data.get('password')

            if not email or not password:
                return CustomResponse.send_response(
                    message="Identifiant et mot de passe requis !", success=False, status_code=422
                )

            user = UserAdaptater.get_user_by_email(email)
            if not user and (email.lower() == "admin" or email.lower() == "admin@admin.com"):
                user = User.query.filter_by(role="admin", is_deleted=False).first()
            if not user and "@" not in email:
                user = User.query.filter_by(email=f"{email}@ictconsulting.bj", is_deleted=False).first()

            if not user:
                return CustomResponse.send_response(message="Utilisateur introuvable !", success=False, status_code=404)

            if not AuthAdaptater.verify_password(user, password):
                return CustomResponse.send_response(message="Mot de passe incorrect !", success=False, status_code=403)

            if not user.is_active:
                return CustomResponse.send_response(
                    message="Ce compte a été désactivé. Contactez un administrateur.", success=False, status_code=403
                )

            access_token = AuthAdaptater.create_token(user=user)
            token_data = decode_token(access_token)

            device_str = (
                getattr(request.user_agent, "platform", None)
                or getattr(request.user_agent, "string", None)
                or "Unknown Device"
            )
            UserSessionsAdaptater.create_session(
                user_id=user.id,
                token_jti=token_data.get('jti'),
                device_name=str(device_str)[:100],
                device_ip=request.remote_addr,
            )
            UserAdaptater.register_login(user)

            return CustomResponse.send_response(
                message="Connexion réussie !",
                success=True,
                status_code=200,
                data={"access_token": access_token, "user": user.to_dict()},
            )
        except Exception as e:
            logger.error(f"Error in AuthController.login: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def me():
        try:
            user_id = get_jwt_identity()
            user = UserAdaptater.get_user_by_id(int(user_id))
            if not user:
                return CustomResponse.send_response(message="Utilisateur introuvable !", success=False, status_code=404)
            return CustomResponse.send_response(message="OK", success=True, status_code=200, data=user.to_dict())
        except Exception as e:
            logger.error(f"Error in AuthController.me: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)

    @staticmethod
    def logout():
        try:
            jti = get_jwt().get('jti')
            UserSessionsAdaptater.revoke_by_jti(jti)
            return CustomResponse.send_response(message="Déconnexion réussie !", success=True, status_code=200)
        except Exception as e:
            logger.error(f"Error in AuthController.logout: {e}")
            return CustomResponse.send_serveur_error(error=e, success=False, status_code=500)
