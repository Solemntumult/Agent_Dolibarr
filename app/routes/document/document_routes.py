from flask import Blueprint
from flask_jwt_extended import jwt_required

from commons.utils.decorators import internal_user_required
from controllers.document.document_controller import DocumentController

document_bp = Blueprint('document', __name__)


@document_bp.route('/<string:modulepart>/<string:ref>', methods=['GET'])
@jwt_required()
@internal_user_required()
def download_document_route(modulepart, ref):
    """Télécharge le PDF officiel Dolibarr (facture, devis) — réservé aux utilisateurs internes."""
    return DocumentController.download(modulepart, ref)
