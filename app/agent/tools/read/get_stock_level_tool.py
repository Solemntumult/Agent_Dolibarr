from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from adaptater.dolibarr.product_adaptater import ProductAdaptater


class GetStockLevelTool:
    """
    Outil exposé au LLM via le tool_registry.
    Sens : READ
    """

    name = "get_stock_level"
    sense = ToolSense.READ

    description = (
        "Retourne le niveau de stock d'un produit précis ou de tous les produits, avec la liste des "
        "produits dont le stock est passé sous le seuil d'alerte configuré (cahier des charges §3.3)."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "product_id": {
                "type": "integer",
                "description": "Identifiant Dolibarr du produit (optionnel — sans lui, tous les produits sont analysés)."
            },
            "threshold": {
                "type": "number",
                "description": "Seuil d'alerte de stock à appliquer (optionnel, par défaut seuil configuré)."
            }
        },
        "required": []
    }

    @staticmethod
    def run(params: dict):
        try:
            product_id = params.get("product_id")
            threshold = params.get("threshold")
            return ProductAdaptater.get_stock_level(product_id=product_id, threshold=threshold)
        except Exception as e:
            logger.error(f"Error in GetStockLevelTool.run: {e}")
            return {"error": str(e)}
