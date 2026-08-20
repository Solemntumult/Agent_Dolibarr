"""Connecteur HTTP vers l'API REST Dolibarr (cahier des charges §4.3).

Tous les appels sont authentifiés par la clé DOLAPIKEY (en-tête DOLAPIKEY) et
pointent vers DOLIBARR_API_URL (ex. http://localhost/dolibarr/api/index.php).
La clé est rattachée à un utilisateur Dolibarr dédié aux privilèges minimaux (§5.1).
"""
import requests

from commons.config.config import Config
from commons.instances.instances import logger


class DolibarrClientAdaptater:

    @staticmethod
    def _headers() -> dict:
        return {
            "DOLAPIKEY": Config.DOLAPIKEY or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def _url(endpoint: str) -> str:
        base = (Config.DOLIBARR_API_URL or "").rstrip("/")
        return f"{base}/{endpoint.lstrip('/')}"

    @staticmethod
    def request(method: str, endpoint: str, params: dict = None, data: dict = None):
        """Exécute une requête vers l'API Dolibarr et retourne le JSON décodé.

        Lève une exception DolibarrClientError en cas d'erreur HTTP.
        """
        try:
            url = DolibarrClientAdaptater._url(endpoint)
            response = requests.request(
                method=method,
                url=url,
                params=params or {},
                json=data,
                headers=DolibarrClientAdaptater._headers(),
                timeout=Config.DOLIBARR_TIMEOUT,
            )
            if response.status_code == 404 and method == "GET":
                # Dolibarr renvoie 404 lorsque aucun enregistrement ne correspond aux filtres
                # Pour les listes (ex: invoices, thirdparties, proposals, products), on retourne une liste vide []
                endpoint_clean = endpoint.strip("/")
                if "/" not in endpoint_clean:
                    return []
                return {}

            if response.status_code >= 400:
                message = response.text[:500] if response.text else f"HTTP {response.status_code}"
                raise DolibarrClientError(f"Dolibarr {method} {endpoint} -> {response.status_code}: {message}")

            if not response.content:
                return {}
            return response.json()
        except DolibarrClientError:
            raise
        except requests.RequestException as e:
            logger.error(f"Dolibarr request failed {method} {endpoint}: {e}")
            raise DolibarrClientError(f"Impossible de joindre l'API Dolibarr ({e})") from e

    @staticmethod
    def get(endpoint: str, params: dict = None):
        return DolibarrClientAdaptater.request("GET", endpoint, params=params)

    @staticmethod
    def post(endpoint: str, data: dict):
        return DolibarrClientAdaptater.request("POST", endpoint, data=data)

    @staticmethod
    def put(endpoint: str, data: dict):
        return DolibarrClientAdaptater.request("PUT", endpoint, data=data)

    @staticmethod
    def is_configured() -> bool:
        return bool(Config.DOLIBARR_API_URL and Config.DOLAPIKEY)


class DolibarrClientError(Exception):
    """Erreur applicative levée quand l'API Dolibarr est injoignable ou refuse la requête."""
