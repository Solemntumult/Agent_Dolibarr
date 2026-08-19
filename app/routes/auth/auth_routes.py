from flask import Blueprint
from flask_jwt_extended import jwt_required

from commons.utils.decorators import internal_user_required
from controllers.auth.auth_controller import AuthController

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['POST'])
def login_route():
    return AuthController.login()


@auth.route('/me', methods=['GET'])
@jwt_required()
@internal_user_required()
def me_route():
    return AuthController.me()


@auth.route('/logout', methods=['POST'])
@jwt_required()
def logout_route():
    return AuthController.logout()
