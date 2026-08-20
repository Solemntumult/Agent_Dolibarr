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


@email.route('/list', methods=['GET'])
@jwt_required()
@internal_user_required()
def list_route():
    return EmailController.list_emails()


@email.route('/<int:email_id>', methods=['GET'])
@jwt_required()
@internal_user_required()
def get_email_route(email_id: int):
    return EmailController.get_email(email_id)


@email.route('/poll', methods=['POST'])
@jwt_required()
@internal_user_required()
def poll_route():
    return EmailController.poll()


@email.route('/<int:email_id>/send-reply', methods=['POST'])
@jwt_required()
@internal_user_required()
def send_reply_route(email_id: int):
    return EmailController.send_reply(email_id)


@email.route('/<int:email_id>/execute-action', methods=['POST'])
@jwt_required()
@internal_user_required()
def execute_action_route(email_id: int):
    return EmailController.execute_action(email_id)


@email.route('/<int:email_id>/reject', methods=['POST'])
@jwt_required()
@internal_user_required()
def reject_route(email_id: int):
    return EmailController.reject(email_id)


@email.route('/simulate', methods=['POST'])
@jwt_required()
@internal_user_required()
def simulate_route():
    return EmailController.simulate()


@email.route('/send-direct', methods=['POST'])
@jwt_required()
@internal_user_required()
def send_direct_route():
    return EmailController.send_direct()
