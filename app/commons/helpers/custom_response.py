from flask import jsonify


class CustomResponse:

    @staticmethod
    def send_response(message, success=True, status_code=200, data=None):
        return jsonify({
            "message": message,
            "success": success,
            "data": data
        }), status_code

    @staticmethod
    def send_serveur_error(error, success=False, status_code=500):
        return jsonify({
            "message": "Erreur serveur",
            "success": success,
            "error": str(error)
        }), status_code
