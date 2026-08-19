"""Construction du contexte LLM optimisé (historique compressé + RAG LangChain).

Utilise LangChain + FAISS pour la recherche sémantique, réduisant le nombre
de tokens en n'envoyant au LLM que les informations pertinentes.
"""
from commons.config.config import Config
from adaptater.conversation.conversation_adaptater import ConversationAdaptater
from services.vector.vector_store_service import VectorStoreService


class ContextBuilder:

    @staticmethod
    def build_history(conversation_id: int, current_message: str) -> list:
        """Historique récent + résumé + contexte RAG vectoriel."""
        limit = Config.LLM_HISTORY_LIMIT
        all_messages = ConversationAdaptater.get_messages(conversation_id, limit=100)
        # Exclure le message courant (dernier user) s'il vient d'être ajouté
        if all_messages and all_messages[-1].get("role") == "user":
            all_messages = all_messages[:-1]

        messages = []
        if len(all_messages) > limit:
            older = all_messages[:-limit]
            summary = ContextBuilder._summarize_older(older)
            if summary:
                messages.append({
                    "role": "system",
                    "content": f"Résumé des échanges précédents :\n{summary}",
                })

        for m in all_messages[-limit:]:
            if m["role"] in ("user", "assistant"):
                content = m["content"]
                if len(content) > Config.LLM_MESSAGE_MAX_CHARS:
                    content = content[:Config.LLM_MESSAGE_MAX_CHARS] + "…"
                messages.append({"role": m["role"], "content": content})

        # Contexte RAG : uniquement les entités pertinentes (réduction tokens)
        vector_ctx = ContextBuilder._vector_context(current_message)
        if vector_ctx:
            messages.append({"role": "system", "content": vector_ctx})

        return messages

    @staticmethod
    def _summarize_older(messages: list) -> str:
        lines = []
        for m in messages:
            if m["role"] not in ("user", "assistant"):
                continue
            prefix = "Utilisateur" if m["role"] == "user" else "Assistant"
            snippet = (m["content"] or "").replace("\n", " ").strip()[:120]
            if snippet:
                lines.append(f"- {prefix} : {snippet}")
        return "\n".join(lines[:8])

    @staticmethod
    def _vector_context(message: str) -> str:
        """Construit le contexte RAG à partir de la recherche vectorielle LangChain.

        Utilise LangChain + FAISS pour ne récupérer que les entités
        (clients, produits) pertinentes pour la requête, réduisant ainsi
        significativement le nombre de tokens envoyés au LLM.
        """
        if not Config.VECTOR_SEARCH_ENABLED or not message:
            return ""

        # Utiliser LangChain RAG si disponible
        try:
            from services.optimization.rag_chain import rag_chain
            if rag_chain.is_configured():
                return rag_chain.get_relevant_context(message)
        except ImportError:
            pass

        # Fallback sur la recherche directe
        client_hits = VectorStoreService.search("client", message, limit=3)
        product_hits = VectorStoreService.search("product", message, limit=2)
        if not client_hits and not product_hits:
            return ""

        parts = ["Contexte métier pertinent (recherche sémantique) :"]
        for hit in client_hits:
            meta = hit.get("metadata") or {}
            parts.append(
                f"- Client #{hit['entity_id']} {meta.get('name', '')} "
                f"({meta.get('email', '')}, {meta.get('town', '')}) [score {hit['score']}]"
            )
        for hit in product_hits:
            meta = hit.get("metadata") or {}
            parts.append(
                f"- Produit #{hit['entity_id']} {meta.get('ref', '')} — {meta.get('label', '')} "
                f"[score {hit['score']}]"
            )
        parts.append("Utilisez les outils pour confirmer et obtenir les données à jour.")
        return "\n".join(parts)
