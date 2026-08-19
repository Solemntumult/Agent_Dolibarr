from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.thirdparty_adaptater import ThirdpartyAdaptater


class GetClientTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : READ
    """

    name = "get_client"
    sense = ToolSense.READ

    description = (
        "Retourne les informations détaillées d'un client (tiers) Dolibarr à partir de son identifiant. "
        "Utilisez search_client d'abord si vous n'avez que le nom."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "client_id": {
                "type": "integer",
                "description": "Identifiant Dolibarr du client (champ 'id' retourné par search_client)."
            }
        },
        "required": ["client_id"]
    }

    @staticmethod
    def run(params: dict):
        try:
            client_id = int(params.get("client_id"))
            return {"client": ThirdpartyAdaptater.get_by_id(client_id)}
        except Exception as e:
            logger.error(f"Error in GetClientTool.run: {e}")
            return {"error": str(e)}
