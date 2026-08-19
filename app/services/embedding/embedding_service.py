"""Service d'embeddings OpenAI pour la recherche vectorielle."""
import openai

from commons.config.config import Config
from commons.instances.instances import logger


class EmbeddingService:

    _cache = {}

    def __init__(self):
        self.client = None
        if Config.OPENAI_API_KEY:
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

    def is_configured(self) -> bool:
        return self.client is not None and Config.VECTOR_SEARCH_ENABLED

    @staticmethod
    def _cache_key(text: str) -> str:
        return text.strip().lower()[:512]

    def embed_text(self, text: str) -> list:
        """Retourne le vecteur d'embedding pour un texte."""
        if not self.client or not text or not text.strip():
            return []
        key = self._cache_key(text)
        if key in EmbeddingService._cache:
            return EmbeddingService._cache[key]
        try:
            response = self.client.embeddings.create(
                model=Config.OPENAI_EMBEDDING_MODEL,
                input=text.strip()[:8000],
            )
            vector = response.data[0].embedding
            if len(EmbeddingService._cache) < 500:
                EmbeddingService._cache[key] = vector
            return vector
        except openai.OpenAIError as e:
            logger.error(f"EmbeddingService.embed_text failed: {e}")
            return []

    def embed_batch(self, texts: list) -> list:
        """Embeddings par lot (max 64 textes)."""
        if not self.client or not texts:
            return []
        clean = [t.strip()[:8000] for t in texts if t and str(t).strip()]
        if not clean:
            return []
        try:
            response = self.client.embeddings.create(
                model=Config.OPENAI_EMBEDDING_MODEL,
                input=clean,
            )
            ordered = [None] * len(clean)
            for item in response.data:
                ordered[item.index] = item.embedding
            return ordered
        except openai.OpenAIError as e:
            logger.error(f"EmbeddingService.embed_batch failed: {e}")
            return []
