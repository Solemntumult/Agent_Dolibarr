from flask import jsonify


def register_error_handlers(app):

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"message": "Ressource introuvable", "success": False}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"message": "Erreur serveur", "success": False}), 500
