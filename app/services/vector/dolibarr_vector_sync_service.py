"""Synchronisation des entités Dolibarr vers l'index vectoriel ChromaDB.

Utilise LangChainVectorStoreService (ChromaDB) pour stocker les embeddings.
"""
from adaptater.dolibarr.product_adaptater import ProductAdaptater
from adaptater.dolibarr.thirdparty_adaptater import ThirdpartyAdaptater
from commons.instances.instances import logger
from services.embedding.embedding_service import EmbeddingService
from services.vector.vector_store_service import VectorStoreService


class DolibarrVectorSyncService:

    @staticmethod
    def _client_text(client: dict) -> str:
        parts = [
            client.get("name") or "",
            client.get("email") or "",
            client.get("town") or "",
            client.get("phone") or "",
            client.get("code_client") or "",
            client.get("note") or "",
        ]
        return " | ".join(p for p in parts if p)

    @staticmethod
    def _product_text(product: dict) -> str:
        parts = [
            product.get("ref") or "",
            product.get("label") or "",
            str(product.get("price_ht") or ""),
        ]
        return " | ".join(p for p in parts if p)

    @staticmethod
    def sync_all() -> dict:
        """Synchronise toutes les entités Dolibarr vers ChromaDB."""
        embedding_service = EmbeddingService()
        if not embedding_service.is_configured():
            return {"success": False, "summary": "Recherche vectorielle désactivée ou OPENAI_API_KEY absente."}

        clients_synced = DolibarrVectorSyncService._sync_clients(embedding_service)
        products_synced = DolibarrVectorSyncService._sync_products(embedding_service)
        total = VectorStoreService.count()
        summary = f"Index vectoriel ChromaDB : {clients_synced} clients, {products_synced} produits ({total} documents)."
        logger.info(summary)
        return {
            "success": True,
            "summary": summary,
            "clients": clients_synced,
            "products": products_synced,
            "total": total,
        }

    @staticmethod
    def _sync_clients(embedding_service: EmbeddingService) -> int:
        try:
            clients = ThirdpartyAdaptater.search(query="", limit=500)
        except Exception as e:
            logger.warning(f"DolibarrVectorSyncService clients: {e}")
            return 0
        if not clients:
            return 0

        texts = [DolibarrVectorSyncService._client_text(c) for c in clients]
        vectors = embedding_service.embed_batch(texts)
        synced = 0
        for client, text, vector in zip(clients, texts, vectors):
            if not vector or not client.get("id"):
                continue
            if VectorStoreService.upsert(
                entity_type="client",
                entity_id=client["id"],
                content_text=text,
                embedding=vector,
                metadata=client,
            ):
                synced += 1
        return synced

    @staticmethod
    def _sync_products(embedding_service: EmbeddingService) -> int:
        try:
            products = ProductAdaptater.list_products(limit=500)
        except Exception as e:
            logger.warning(f"DolibarrVectorSyncService products: {e}")
            return 0
        if not products:
            return 0

        texts = [DolibarrVectorSyncService._product_text(p) for p in products]
        vectors = embedding_service.embed_batch(texts)
        synced = 0
        for product, text, vector in zip(products, texts, vectors):
            if not vector or not product.get("id"):
                continue
            if VectorStoreService.upsert(
                entity_type="product",
                entity_id=product["id"],
                content_text=text,
                embedding=vector,
                metadata=product,
            ):
                synced += 1
        return synced
