"""Spécifications Swagger (flasgger) pour le module d'authentification.

Réservé aux utilisateurs internes ICT Consulting (cahier des charges §5.1 :
authentification obligatoire, aucun accès anonyme à l'application web).
"""

login_doc = {
    "tags": ["Auth"],
    "summary": "Connexion d'un utilisateur interne",
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "password": {"type": "string"},
                },
                "required": ["email", "password"],
            },
        }
    ],
    "responses": {
        200: {"description": "Connexion réussie, retourne un access_token JWT"},
        403: {"description": "Mot de passe incorrect ou compte désactivé"},
        404: {"description": "Utilisateur introuvable"},
    },
}

me_doc = {
    "tags": ["Auth"],
    "summary": "Récupérer le profil de l'utilisateur interne connecté",
    "security": [{"Bearer": []}],
    "responses": {200: {"description": "Profil utilisateur"}},
}

logout_doc = {
    "tags": ["Auth"],
    "summary": "Déconnexion — révoque le token JWT courant",
    "security": [{"Bearer": []}],
    "responses": {200: {"description": "Déconnexion réussie"}},
}
