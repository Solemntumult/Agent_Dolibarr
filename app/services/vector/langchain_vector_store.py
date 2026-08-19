"""Service vectoriel LangChain + FAISS pour la recherche sémantique.

Utilise LangChain avec FAISS (Facebook AI Similarity Search) pour :
- Stocker les embeddings des entités Dolibarr (clients, produits)
- Effectuer des recherches sémantiques rapides
- Réduire le nombre de tokens en n'envoyant que le contexte pertinent au LLM

Avantages par rapport à l'ancien SQLite :
- Recherche plus rapide (index FAISS optimisé)
- Gestion automatique des documents LangChain
- Intégration native avec les chaînes RAG
"""
import os
import json
import pickle
from typing import Optional, List
from pathlib import Path

from commons.config.config import Config
from commons.instances.instances import logger

# LangChain imports
try:
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    from langchain_community.vectorstores.faiss import FAISS
    from langchain_openai import OpenAIEmbeddings
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    logger.warning("LangChain non disponible — recherche vectorielle désactivée")


class LangChainVectorStore:
    """Service vectoriel basé sur LangChain + FAISS."""

    _instance = None
    _vector_stores = {}  # {entity_type: FAISS}
    _embeddings = None
    _persist_dir = None

    def __init__(self):
        if not HAS_LANGCHAIN:
            logger.error("LangChain non installé — impossible d'initialiser le vector store")
            return

        # Chemin de persistance pour les index FAISS
        self._persist_dir = Path(__file__).parent.parent.parent.parent / "faiss_index"
        self._persist_dir.mkdir(exist_ok=True)

        # Initialiser les embeddings OpenAI
        if Config.OPENAI_API_KEY:
            self._embeddings = OpenAIEmbeddings(
                model=Config.OPENAI_EMBEDDING_MODEL,
                openai_api_key=Config.OPENAI_API_KEY
            )
            logger.info(f"LangChainVectorStore initialisé avec embeddings {Config.OPENAI_EMBEDDING_MODEL}")
        else:
            logger.warning("OPENAI_API_KEY non configurée — embeddings non disponibles")

    @classmethod
    def get_instance(cls) -> "LangChainVectorStore":
        """Retourne l'instance singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_configured(self) -> bool:
        """Vérifie si le service est opérationnel."""
        return (
            HAS_LANGCHAIN
            and self._embeddings is not None
            and Config.VECTOR_SEARCH_ENABLED
        )

    def _get_store(self, entity_type: str) -> Optional[FAISS]:
        """Récupère ou crée le vector store pour un type d'entité."""
        if not self.is_configured():
            return None

        # Vérifier le cache en mémoire
        if entity_type in self._vector_stores:
            return self._vector_stores[entity_type]

        # Essayer de charger depuis le disque
        store_path = self._persist_dir / f"{entity_type}"
        if store_path.exists():
            try:
                store = FAISS.load_local(
                    str(store_path),
                    self._embeddings,
                    allow_dangerous_deserialization=True
                )
                self._vector_stores[entity_type] = store
                logger.info(f"Vector store {entity_type} chargé depuis {store_path}")
                return store
            except Exception as e:
                logger.warning(f"Erreur chargement vector store {entity_type}: {e}")

        return None

    def upsert(self, entity_type: str, entity_id: int, content_text: str,
               embedding: list, metadata: dict = None) -> bool:
        """Insère ou met à jour un document dans le vector store."""
        if not self.is_configured():
            return False

        try:
            # Créer le document LangChain
            doc_metadata = {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "content_text": content_text[:1000],
            }
            if metadata:
                # Ajouter les métadonnées plates (LangChain ne supporte pas les nested)
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        doc_metadata[key] = value

            document = Document(
                page_content=content_text[:500],
                metadata=doc_metadata
            )

            # Récupérer ou créer le vector store
            store = self._get_store(entity_type)

            if store is None:
                # Créer un nouveau vector store
                store = FAISS.from_documents([document], self._embeddings)
            else:
                # Ajouter le document (upsert par entity_id)
                # Pour FAISS, on ne peut pas faire d'upsert directement,
                # on reconstruit avec tous les documents
                existing_docs = store.similarity_search("", k=10000)  # Récupérer tout
                # Filtrer l'ancien document avec le même entity_id
                filtered_docs = [
                    d for d in existing_docs
                    if d.metadata.get("entity_id") != entity_id
                ]
                filtered_docs.append(document)
                # Reconstruire le vector store
                store = FAISS.from_documents(filtered_docs, self._embeddings)

            self._vector_stores[entity_type] = store

            # Persister sur disque
            store_path = self._persist_dir / f"{entity_type}"
            store.save_local(str(store_path))

            return True
        except Exception as e:
            logger.error(f"LangChainVectorStore.upsert failed: {e}")
            return False

    def search(self, entity_type: str, query: str, limit: int = 5,
               min_score: float = None) -> list:
        """Recherche sémantique dans le vector store.

        Retourne une liste de résultats avec score, entity_id, metadata, content_text.
        """
        if not self.is_configured() or not query or not query.strip():
            return []

        min_score = min_score if min_score is not None else Config.VECTOR_MIN_SCORE

        store = self._get_store(entity_type)
        if not store:
            return []

        try:
            # Recherche avec scores
            results = store.similarity_search_with_score(query, k=limit * 2)

            formatted_results = []
            for doc, distance in results:
                # FAISS retourne la distance L2, on convertit en score de similarité
                # Plus la distance est petite, plus c'est pertinent
                score = 1.0 / (1.0 + distance)  # Normaliser entre 0 et 1

                if score < min_score:
                    continue

                formatted_results.append({
                    "score": round(score, 4),
                    "entity_id": doc.metadata.get("entity_id"),
                    "entity_type": entity_type,
                    "content_text": doc.metadata.get("content_text", doc.page_content),
                    "metadata": doc.metadata,
                })

            # Trier par score décroissant
            formatted_results.sort(key=lambda x: x["score"], reverse=True)
            return formatted_results[:limit]

        except Exception as e:
            logger.error(f"LangChainVectorStore.search failed: {e}")
            return []

    def get_rag_context(self, query: str, entity_types: list = None, limit: int = 3) -> str:
        """Génère un contexte RAG pour réduire les tokens envoyés au LLM.

        Cette méthode est conçue pour être utilisée par le ContextBuilder
        afin d'envoyer uniquement les informations pertinentes.
        """
        if not self.is_configured() or not query:
            return ""

        entity_types = entity_types or ["client", "product"]
        context_parts = []

        for entity_type in entity_types:
            hits = self.search(entity_type, query, limit=limit)
            if hits:
                context_parts.append(f"\n--- {entity_type.upper()}S PERTINENTS ---")
                for hit in hits:
                    meta = hit.get("metadata") or {}
                    if entity_type == "client":
                        context_parts.append(
                            f"• Client #{hit['entity_id']}: {meta.get('name', 'N/A')} "
                            f"(Email: {meta.get('email', 'N/A')}, Ville: {meta.get('town', 'N/A')}) "
                            f"[pertinence: {hit['score']:.2f}]"
                        )
                    elif entity_type == "product":
                        context_parts.append(
                            f"• Produit #{hit['entity_id']}: {meta.get('ref', 'N/A')} - "
                            f"{meta.get('label', 'N/A')} "
                            f"(Prix HT: {meta.get('price_ht', 'N/A')} €) "
                            f"[pertinence: {hit['score']:.2f}]"
                        )

        return "\n".join(context_parts)

    def count(self, entity_type: str = None) -> int:
        """Compte le nombre de documents indexés."""
        if not self.is_configured():
            return 0

        total = 0
        try:
            if entity_type:
                store = self._get_store(entity_type)
                if store:
                    total = len(store.docstore._dict)
            else:
                for etype in ["client", "product"]:
                    store = self._get_store(etype)
                    if store:
                        total += len(store.docstore._dict)
        except Exception as e:
            logger.error(f"LangChainVectorStore.count failed: {e}")

        return total

    def clear(self, entity_type: str = None):
        """Supprime tous les documents d'un type ou de tous les types."""
        if not self.is_configured():
            return

        try:
            types_to_clear = [entity_type] if entity_type else ["client", "product"]
            for etype in types_to_clear:
                # Supprimer de la mémoire
                self._vector_stores.pop(etype, None)
                # Supprimer du disque
                store_path = self._persist_dir / f"{etype}"
                if store_path.exists():
                    import shutil
                    shutil.rmtree(store_path)
        except Exception as e:
            logger.error(f"LangChainVectorStore.clear failed: {e}")


# Instance singleton
langchain_vector_store = LangChainVectorStore.get_instance()
