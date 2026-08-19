from flask import Blueprint
from flask_jwt_extended import jwt_required

from commons.utils.decorators import internal_user_required
from controllers.email.email_controller import EmailController

email = Blueprint('email', __name__)


@email.route('/status', methods=['GET'])
@jwt_required()
@internal_user_required()
def status_route():
    return EmailController.status()


@email.route('/poll', methods=['POST'])
@jwt_required()
@internal_user_required()
def poll_route():
    return EmailController.poll()
