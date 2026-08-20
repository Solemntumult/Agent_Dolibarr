"""Construction du contexte LLM optimisé (historique compressé + RAG LangChain).

Utilise LangChain + FAISS pour la recherche sémantique, réduisant le nombre
de tokens en n'envoyant au LLM que les informations pertinentes.
"""
import re

from commons.config.config import Config
from adaptater.conversation.conversation_adaptater import ConversationAdaptater
from services.vector.vector_store_service import VectorStoreService

# Pattern pour détecter les réponses courtes de confirmation
_SHORT_REPLY_PATTERN = re.compile(
    r"^(non|oui|vas-y|vas y|ok|d'accord|daccord|confirme|valide|crée|cree|"
    r"procède|procede|fais-le|fais le|go|c'est bon|c est bon|aucun|aucune)\b",
    re.IGNORECASE,
)


class ContextBuilder:

    @staticmethod
    def _is_short_reply(message: str) -> bool:
        """Détecte si le message est une réponse courte de confirmation."""
        text = (message or "").strip()
        return len(text) <= 30 or bool(_SHORT_REPLY_PATTERN.match(text))

    @staticmethod
    def _compress_assistant_message(content: str) -> str:
        """Compresse un message assistant en supprimant les tableaux Markdown et blocs verbeux."""
        if not content or len(content) <= 200:
            return content
        lines = content.split("\n")
        compressed = []
        in_table = False
        table_skipped = False
        for line in lines:
            stripped = line.strip()
            # Détection des lignes de tableau Markdown
            if stripped.startswith("|") and "|" in stripped[1:]:
                if not in_table:
                    in_table = True
                    table_skipped = False
                if not table_skipped:
                    compressed.append(line)  # Garder la première ligne (en-tête)
                    table_skipped = True
                continue
            else:
                in_table = False
            # Supprimer les lignes de séparateur de tableau
            if re.match(r"^\s*\|[\s\-:|]+\|\s*$", stripped):
                continue
            compressed.append(line)
        result = "\n".join(compressed)
        max_chars = Config.LLM_MESSAGE_MAX_CHARS
        if len(result) > max_chars:
            result = result[:max_chars] + "…"
        return result

    @staticmethod
    def build_history(conversation_id: int, current_message: str) -> list:
        """Historique récent + résumé + contexte RAG vectoriel."""
        is_short = ContextBuilder._is_short_reply(current_message)
        limit = Config.LLM_SHORT_REPLY_HISTORY_LIMIT if is_short else Config.LLM_HISTORY_LIMIT

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
                if m["role"] == "assistant":
                    content = ContextBuilder._compress_assistant_message(content)
                elif len(content) > Config.LLM_MESSAGE_MAX_CHARS:
                    content = content[:Config.LLM_MESSAGE_MAX_CHARS] + "…"
                messages.append({"role": m["role"], "content": content})

        # Contexte RAG : pas pour les réponses courtes (inutile et coûteux)
        if not is_short:
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
            snippet = (m["content"] or "").replace("\n", " ").strip()[:80]
            if snippet:
                lines.append(f"- {prefix} : {snippet}")
        return "\n".join(lines[:6])

    @staticmethod
    def _vector_context(message: str) -> str:
        """Construit le contexte RAG à partir de la recherche vectorielle LangChain."""
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

        parts = ["Contexte métier pertinent :"]
        for hit in client_hits:
            meta = hit.get("metadata") or {}
            parts.append(
                f"- Client #{hit['entity_id']} {meta.get('name', '')} "
                f"({meta.get('town', '')})"
            )
        for hit in product_hits:
            meta = hit.get("metadata") or {}
            parts.append(
                f"- Produit #{hit['entity_id']} {meta.get('ref', '')} — {meta.get('label', '')}"
            )
        return "\n".join(parts)

