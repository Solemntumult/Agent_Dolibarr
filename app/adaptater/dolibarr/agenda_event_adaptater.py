"""Adaptateur agenda / événements — création d'événements (relances, actions commerciales).

Point d'accès (cahier des charges §4.3, Annexe B) : /agendaevents (écriture).
"""
from datetime import datetime, timezone

from adaptater.dolibarr.dolibarr_client_adaptater import DolibarrClientAdaptater, DolibarrClientError
from commons.instances.instances import logger


class AgendaEventAdaptater:

    @staticmethod
    def list_upcoming(limit: int = 5) -> list:
        """Liste les prochains événements à venir (agenda)."""
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            params = {
                "limit": min(limit, 20),
                "sortfield": "t.datep",
                "sortorder": "ASC",
                "sqlfilters": f"(t.datep:>=:'{now.strftime('%Y-%m-%d %H:%M:%S')}')",
            }
            raw = DolibarrClientAdaptater.get("agendaevents", params=params)
            events = []
            for ev in (raw if isinstance(raw, list) else []):
                events.append({
                    "id": ev.get("id"),
                    "label": ev.get("label") or ev.get("libelle") or "",
                    "date": ev.get("datep") or ev.get("datec"),
                    "type": ev.get("type_code") or ev.get("type_label") or "",
                    "note": ev.get("note") or "",
                })
            return events
        except DolibarrClientError as e:
            logger.warning(f"AgendaEventAdaptater.list_upcoming failed: {e}")
            return []

    @staticmethod
    def create(data: dict) -> dict:
        """Crée un événement agenda (journalisation d'une action, ex. relance d'impayé).

        data: label, datep (YYYY-MM-DD HH:MM:SS), type_code (ex. AC_ACT, AC_OTH), note,
        thirdparty_id (optionnel).
        """
        try:
            if not data.get("label"):
                raise DolibarrClientError("Le libellé de l'événement est obligatoire.")
            # Codes de type d'action valides côté Dolibarr (llx_c_actioncomm)
            valid_codes = {"AC_INT", "AC_OTH", "AC_OTH_AUTO", "AC_RDV", "AC_TEL"}
            type_code = data.get("type_code", "AC_OTH")
            if type_code not in valid_codes:
                type_code = "AC_OTH"
            payload = {
                "label": data.get("label"),
                "datep": data.get("datep") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "type_code": type_code,
                "note": data.get("note", ""),
                "location": data.get("location", ""),
                # Propriétaire de l'événement : utilisateur rattaché à la clé API (admin, id 1).
                "userownerid": int(data.get("userownerid", 1)),
            }
            if data.get("thirdparty_id"):
                payload["socid"] = int(data.get("thirdparty_id"))
            result = DolibarrClientAdaptater.post("agendaevents", payload)
            event_id = result if isinstance(result, int) else (result.get("id") if isinstance(result, dict) else None)
            if not event_id:
                raise DolibarrClientError(f"Création d'événement sans identifiant retourné: {result}")
            return {"id": event_id}
        except DolibarrClientError as e:
            logger.error(f"AgendaEventAdaptater.create failed: {e}")
            raise e
