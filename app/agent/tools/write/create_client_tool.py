from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.thirdparty_adaptater import ThirdpartyAdaptater


class CreateClientTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : WRITE — soumis à confirmation avant exécution (§3.2, §5.1).
    """

    name = "create_client"
    sense = ToolSense.WRITE

    description = (
        "Crée un nouveau client (tiers) dans Dolibarr. APPELEZ cet outil pour toute demande de création "
        "de client : l'action sera enregistrée en attente de confirmation de l'utilisateur avant "
        "l'écriture définitive."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Nom / raison sociale du client."},
            "email": {"type": "string", "description": "Adresse e-mail (optionnelle)."},
            "phone": {"type": "string", "description": "Numéro de téléphone (optionnel)."},
            "address": {"type": "string", "description": "Adresse postale (optionnelle)."},
            "city": {"type": "string", "description": "Ville (optionnelle)."},
            "zip": {"type": "string", "description": "Code postal (optionnel)."},
            "note": {"type": "string", "description": "Note publique sur le client (optionnelle)."}
        },
        "required": ["name"]
    }

    @staticmethod
    def run(params: dict):
        try:
            return ThirdpartyAdaptater.create(params)
        except Exception as e:
            logger.error(f"Error in CreateClientTool.run: {e}")
            return {"error": str(e)}
