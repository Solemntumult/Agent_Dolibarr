"""Service OpenAI — appel au modèle GPT avec function calling (cahier des charges §4.2).

Le modèle ne se connecte jamais directement à Dolibarr : il reçoit les définitions
d'outils du backend, décide lesquels appeler, et le backend exécute réellement les
appels (boucle orchestrée par AgentOrchestrator).
"""
import openai

from commons.config.config import Config
from commons.instances.instances import logger

MODEL_BY_TIER = {
    "light": lambda: Config.OPENAI_MODEL_LIGHT,
    "balanced": lambda: Config.OPENAI_MODEL_BALANCED,
    "advanced": lambda: Config.OPENAI_MODEL_ADVANCED,
}


class OpenaiService:

    def __init__(self):
        self.client = None
        if Config.OPENAI_API_KEY:
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

    def is_configured(self) -> bool:
        return self.client is not None

    @staticmethod
    def resolve_model(tier: str = None) -> str:
        return MODEL_BY_TIER.get(tier or "balanced", MODEL_BY_TIER["balanced"])()

    def chat(self, messages: list, tools: list = None, tier: str = "balanced",
             temperature: float = 0.3, max_tokens: int = 2000):
        """Un seul appel au modèle. Retourne (contenu, tool_calls, usage).

        tool_calls: liste de dicts {id, name, arguments} à exécuter par le backend.
        """
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY non configurée — impossible d'appeler le modèle.")

        model = OpenaiService.resolve_model(tier)
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message

            tool_calls = []
            for call in (message.tool_calls or []):
                try:
                    import json
                    arguments = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                tool_calls.append({
                    "id": call.id,
                    "name": call.function.name,
                    "arguments": arguments,
                })

            usage = response.usage
            return (
                message.content or "",
                tool_calls,
                {
                    "model": model,
                    "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                    "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
                },
            )
        except openai.RateLimitError as e:
            logger.error(f"OpenaiService.chat rate limit / quota error: {e}")
            raise RuntimeError(
                "Le compte OpenAI n'a plus de crédits disponibles (Quota épuisé / 429). "
                "Veuillez recharger vos crédits sur platform.openai.com."
            ) from e
        except openai.AuthenticationError as e:
            logger.error(f"OpenaiService.chat auth error: {e}")
            raise RuntimeError(
                "Clé API OpenAI invalide ou révoquée (401). "
                "Veuillez vérifier votre variable OPENAI_API_KEY."
            ) from e
        except openai.OpenAIError as e:
            logger.error(f"OpenaiService.chat failed: {e}")
            raise RuntimeError(f"Erreur OpenAI : {e}") from e
