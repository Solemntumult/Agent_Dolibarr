"""Chaîne RAG (Retrieval-Augmented Generation) avec LangChain.

Objectif : Réduire le nombre de tokens envoyés au LLM en ne récupérant
que les informations pertinentes pour chaque requête.

Avantages :
- Envoie uniquement le contexte pertinent (clients, produits concernés)
- Réduit significativement les coûts OpenAI
- Améliore la qualité des réponses (moins de bruit)
"""
from typing import Optional

from commons.config.config import Config
from commons.instances.instances import logger


class RAGChain:
    """Chaîne RAG pour la recherche contextuelle Dolibarr."""

    def __init__(self):
        self._vector_store = None
        self._init_vector_store()

    def _init_vector_store(self):
        """Initialise le vector store LangChain."""
        try:
            from services.vector.langchain_vector_store import langchain_vector_store
            self._vector_store = langchain_vector_store
        except ImportError:
            logger.warning("LangChain vector store non disponible")

    def is_configured(self) -> bool:
        """Vérifie si la chaîne RAG est opérationnelle."""
        return (
            self._vector_store is not None
            and self._vector_store.is_configured()
        )

    def get_relevant_context(self, query: str, entity_types: list = None,
                            max_tokens_approx: int = 500) -> str:
        """Récupère le contexte pertinent pour une requête.

        Args:
            query: La requête de l'utilisateur
            entity_types: Types d'entités à rechercher (défaut: clients et produits)
            max_tokens_approx: Approximation du nombre max de tokens à retourner

        Returns:
            Le contexte pertinent formaté pour le LLM
        """
        if not self.is_configured() or not query:
            return ""

        entity_types = entity_types or ["client", "product"]

        try:
            # Utiliser le vector store pour récupérer le contexte RAG
            context = self._vector_store.get_rag_context(
                query,
                entity_types=entity_types,
                limit=3  # Limiter à 3 résultats par type
            )

            # Estimer et limiter la taille (approximation : 1 token ≈ 4 caractères)
            max_chars = max_tokens_approx * 4
            if len(context) > max_chars:
                context = context[:max_chars] + "\n... (contexte tronqué)"

            return context

        except Exception as e:
            logger.error(f"RAGChain.get_relevant_context failed: {e}")
            return ""

    def build_messages_with_rag(self, system_prompt: str, user_message: str,
                               conversation_history: list = None) -> list:
        """Construit les messages pour le LLM avec contexte RAG.

        Args:
            system_prompt: Le prompt système de base
            user_message: Le message utilisateur
            conversation_history: L'historique de la conversation (optionnel)

        Returns:
            La liste des messages formatée pour le LLM
        """
        messages = [{"role": "system", "content": system_prompt}]

        # Ajouter l'historique compressé
        if conversation_history:
            for msg in conversation_history[-Config.LLM_HISTORY_LIMIT:]:
                if msg.get("role") in ("user", "assistant"):
                    content = msg.get("content", "")
                    if len(content) > Config.LLM_MESSAGE_MAX_CHARS:
                        content = content[:Config.LLM_MESSAGE_MAX_CHARS] + "…"
                    messages.append({"role": msg["role"], "content": content})

        # Récupérer le contexte RAG
        rag_context = self.get_relevant_context(user_message)
        if rag_context:
            messages.append({
                "role": "system",
                "content": f"Contexte pertinent pour la requête :\n{rag_context}"
            })

        # Ajouter le message utilisateur
        messages.append({"role": "user", "content": user_message})

        return messages


# Instance singleton
rag_chain = RAGChain()
