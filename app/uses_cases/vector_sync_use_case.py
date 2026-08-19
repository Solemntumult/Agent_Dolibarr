"""Use case : synchronisation de l'index vectoriel Dolibarr."""
from services.vector.dolibarr_vector_sync_service import DolibarrVectorSyncService


class VectorSyncUseCase:

    @staticmethod
    def execute(task=None) -> dict:
        return DolibarrVectorSyncService.sync_all()


UseCase = VectorSyncUseCase
