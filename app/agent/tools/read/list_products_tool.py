from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.product_adaptater import ProductAdaptater


class ListProductsTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : READ
    """

    name = "list_products"
    sense = ToolSense.READ

    description = (
        "Liste le catalogue produits/services de Dolibarr (référence, libellé, prix, stock). "
        "Recherche optionnelle par libellé ou référence."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "search": {
                "type": "string",
                "description": "Filtre sur le libellé ou la référence du produit. Optionnel."
            },
            "limit": {
                "type": "integer",
                "description": "Nombre maximal de résultats (défaut 50)."
            }
        },
        "required": []
    }

    @staticmethod
    def run(params: dict):
        try:
            search = params.get("search")
            limit = params.get("limit", 50)
            return {"produits": ProductAdaptater.list_products(search=search, limit=limit)}
        except Exception as e:
            logger.error(f"Error in ListProductsTool.run: {e}")
            return {"error": str(e)}
