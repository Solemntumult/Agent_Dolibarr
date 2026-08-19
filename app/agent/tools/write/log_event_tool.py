from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.agenda_event_adaptater import AgendaEventAdaptater


class LogEventTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : WRITE — soumis à confirmation avant exécution (§3.2, §5.1).
    """

    name = "log_event"
    sense = ToolSense.WRITE

    description = (
        "Journalise une action dans l'agenda Dolibarr (ex. enregistrement d'une relance envoyée à un "
        "client). APPELEZ cet outil pour journaliser une action : l'action sera enregistrée en attente "
        "de confirmation de l'utilisateur avant toute écriture."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "label": {"type": "string", "description": "Libellé de l'événement (ex. 'Relance impayé envoyée')."},
            "type_code": {
                "type": "string",
                "description": "Type d'action Dolibarr valide : AC_OTH (autre, défaut), AC_TEL (appel téléphonique), "
                                "AC_RDV (rendez-vous), AC_INT (tâche interne). Optionnel."
            },
            "thirdparty_id": {
                "type": "integer",
                "description": "Identifiant Dolibarr du client concerné (optionnel)."
            },
            "note": {"type": "string", "description": "Note détaillée (optionnelle)."}
        },
        "required": ["label"]
    }

    @staticmethod
    def run(params: dict):
        try:
            return AgendaEventAdaptater.create(params)
        except Exception as e:
            logger.error(f"Error in LogEventTool.run: {e}")
            return {"error": str(e)}
