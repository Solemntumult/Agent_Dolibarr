"""Registre central des outils exposés au LLM (cahier des charges §4.2, §4.3).

Le modèle ne se connecte jamais directement à Dolibarr : il décide quels outils
appeler, le backend exécute réellement l'appel via ce registre, puis renvoie le
résultat au modèle. Les outils WRITE sont soumis à confirmation (§3.2, §5.1).
"""
from commons.enums.tool_sense.tool_sense import ToolSense
from commons.instances.instances import logger
from services.optimization.query_cache_service import QueryCacheService
from services.optimization.tool_result_compressor import ToolResultCompressor

from agent.tools.read.search_client_tool import SearchClientTool
from agent.tools.read.get_client_tool import GetClientTool
from agent.tools.read.list_unpaid_invoices_tool import ListUnpaidInvoicesTool
from agent.tools.read.get_invoice_tool import GetInvoiceTool
from agent.tools.read.get_quote_tool import GetQuoteTool
from agent.tools.read.get_document_tool import GetDocumentTool
from agent.tools.read.list_products_tool import ListProductsTool
from agent.tools.read.list_quotes_tool import ListQuotesTool
from agent.tools.read.get_stock_level_tool import GetStockLevelTool
from agent.tools.read.get_sales_statistics_tool import GetSalesStatisticsTool

from agent.tools.write.create_client_tool import CreateClientTool
from agent.tools.write.create_quote_tool import CreateQuoteTool
from agent.tools.write.create_invoice_tool import CreateInvoiceTool
from agent.tools.write.convert_quote_to_invoice_tool import ConvertQuoteToInvoiceTool
from agent.tools.write.log_event_tool import LogEventTool

_ALL_TOOLS = [
    # Lecture
    SearchClientTool,
    GetClientTool,
    ListUnpaidInvoicesTool,
    GetInvoiceTool,
    GetQuoteTool,
    GetDocumentTool,
    ListProductsTool,
    ListQuotesTool,
    GetStockLevelTool,
    GetSalesStatisticsTool,
    # Écriture (soumise à confirmation)
    CreateClientTool,
    CreateQuoteTool,
    CreateInvoiceTool,
    ConvertQuoteToInvoiceTool,
    LogEventTool,
]


class ToolRegistry:

    @staticmethod
    def all_tools() -> list:
        return _ALL_TOOLS

    @staticmethod
    def get_tool(name: str):
        for tool_cls in _ALL_TOOLS:
            if tool_cls.name == name:
                return tool_cls
        return None

    @staticmethod
    def get_function_definitions(tool_sense: str = None, tool_names: set = None) -> list:
        """Définitions OpenAI (format function calling) des outils, filtrées par sens ou par nom."""
        definitions = []
        for tool_cls in _ALL_TOOLS:
            if tool_sense and tool_cls.sense != tool_sense:
                continue
            if tool_names and tool_cls.name not in tool_names:
                continue
            definitions.append({
                "type": "function",
                "function": {
                    "name": tool_cls.name,
                    "description": getattr(tool_cls, "description", tool_cls.name),
                    "parameters": tool_cls.input_schema,
                },
            })
        return definitions

    @staticmethod
    def execute(name: str, params: dict) -> dict:
        """Exécute un outil. Retourne toujours un dict (résultat ou erreur) consommable par le LLM."""
        tool_cls = ToolRegistry.get_tool(name)
        if not tool_cls:
            return {"error": f"Outil inconnu: {name}"}
        try:
            cached = QueryCacheService.get(name, params or {})
            if cached is not None:
                logger.info(f"Tool cache hit: {name}")
                return cached

            logger.info(f"Tool execution: {name} params={params}")
            result = tool_cls.run(params or {})
            payload = {"tool": name, "result": result}
            payload = ToolResultCompressor.compress(name, payload)
            QueryCacheService.set(name, params or {}, payload)
            return payload
        except Exception as e:
            logger.error(f"ToolRegistry.execute({name}) failed: {e}")
            return {"tool": name, "error": str(e)}

    @staticmethod
    def execute_write_after_confirmation(name: str, params: dict) -> dict:
        """Exécute une écriture après confirmation (décorateur @confirmation_required)."""
        return ToolRegistry.execute(name, params)

    @staticmethod
    def is_write_tool(name: str) -> bool:
        tool_cls = ToolRegistry.get_tool(name)
        return bool(tool_cls and tool_cls.sense == ToolSense.WRITE)
