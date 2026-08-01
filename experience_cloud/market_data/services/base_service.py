from abc import ABC, abstractmethod

from experience_cloud.market_data.schemas import DataDumpResponseSchema, DataDumpSchema


class BaseDataDumpService(ABC):
    """The strict contract that all Data Dump Providers MUST follow."""

    @abstractmethod
    def execute(self, schema: DataDumpSchema) -> DataDumpResponseSchema:
        """Executes the API fetching logic and handles the database Upserts."""
        pass


