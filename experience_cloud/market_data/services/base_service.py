from experience_cloud.market_data.schemas import DataDumpResponseSchema
from experience_cloud.market_data.schemas import DataDumpSchema
from abc import ABC, abstractmethod

class BaseDataDumpService(ABC):
    """
    The strict contract that all Data Dump Providers MUST follow.
    """
    
    @abstractmethod
    def execute(self, schema: DataDumpSchema) -> DataDumpResponseSchema:
        """
        Executes the API fetching logic and handles the database Upserts.
        """
        pass
