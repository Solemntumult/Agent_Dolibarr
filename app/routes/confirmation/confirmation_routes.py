from flask import Blueprint
from flask_jwt_extended import jwt_required

from commons.utils.decorators import internal_user_required
from controllers.confirmation.confirmation_controller import ConfirmationController

confirmation = Blueprint('confirmation', __name__)


@confirmation.route('/', methods=['GET'])
@jwt_required()
@internal_user_required()
def list_all_route():
    return ConfirmationController.list_all()


@confirmation.route('/pending', methods=['GET'])
@jwt_required()
@internal_user_required()
def list_pending_route():
    return ConfirmationController.list_pending()


@confirmation.route('/<int:confirmation_id>', methods=['GET'])
@jwt_required()
@internal_user_required()
def get_route(confirmation_id):
    return ConfirmationController.get(confirmation_id)


@confirmation.route('/<int:confirmation_id>/confirm', methods=['POST'])
@jwt_required()
@internal_user_required()
def confirm_route(confirmation_id):
    return ConfirmationController.confirm(confirmation_id)


@confirmation.route('/<int:confirmation_id>/reject', methods=['POST'])
@jwt_required()
@internal_user_required()
def reject_route(confirmation_id):
    return ConfirmationController.reject(confirmation_id)


@confirmation.route('/<int:confirmation_id>/document', methods=['GET'])
@jwt_required()
@internal_user_required()
def download_document_route(confirmation_id):
    """Télécharge le PDF du document créé après confirmation (§4.4, §5.1)."""
    return ConfirmationController.download_document(confirmation_id)
