"""Stockage et recherche vectorielle — LangChain + FAISS.

Ce module est le point d'entrée unique pour la recherche sémantique.
Il délègue l'implémentation à LangChainVectorStore (FAISS).
"""
from commons.config.config import Config
from commons.instances.instances import logger


class VectorStoreService:
    """Facade statique qui délegue à LangChainVectorStore (FAISS)."""

    @staticmethod
    def _get_backend():
        from services.vector.langchain_vector_store import langchain_vector_store
        return langchain_vector_store

    @staticmethod
    def upsert(entity_type: str, entity_id: int, content_text: str,
               embedding: list, metadata: dict = None) -> bool:
        try:
            return VectorStoreService._get_backend().upsert(
                entity_type, entity_id, content_text, embedding, metadata
            )
        except Exception as e:
            logger.error(f"VectorStoreService.upsert failed: {e}")
            return False

    @staticmethod
    def count(entity_type: str = None) -> int:
        try:
            return VectorStoreService._get_backend().count(entity_type)
        except Exception as e:
            logger.error(f"VectorStoreService.count failed: {e}")
            return 0

    @staticmethod
    def search(entity_type: str, query: str, limit: int = 5,
               min_score: float = None) -> list:
        """Recherche sémantique. Retourne [{score, entity_id, metadata, content_text}]."""
        try:
            return VectorStoreService._get_backend().search(
                entity_type, query, limit, min_score
            )
        except Exception as e:
            logger.error(f"VectorStoreService.search failed: {e}")
            return []

    @staticmethod
    def clear(entity_type: str = None):
        try:
            VectorStoreService._get_backend().clear(entity_type)
        except Exception as e:
            logger.error(f"VectorStoreService.clear failed: {e}")
