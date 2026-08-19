"""Point d'entrée WSGI pour le déploiement en production (gunicorn) — cf. cahier des
charges §7 (livrable : application déployée et sécurisée sur le VPS) et §4.8.

Exemple d'utilisation :
    gunicorn --workers 3 --bind 0.0.0.0:5000 wsgi:app
Le port par défaut est configurable via la variable d'environnement PORT.
"""
import os
from __init__ import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
