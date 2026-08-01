from rest_framework.exceptions import APIException


class SchedulerBaseException(APIException):
    """Base APIException subclass for tracking and escalating scheduler-related task failures."""
    status_code = 500
    default_detail = 'Scheduler operation failed.'
    default_code = 'scheduler_error'

    def __init__(self, message=None, extra=None):
        """Initialize the exception with an optional message and extra details."""
        self.message = message or self.default_detail
        self.extra = extra
        super().__init__(detail=self.message)

class DataProcessingException(APIException):
    """APIException subclass for tracking failures during JSON structural processing and orchestration."""
    status_code = 500
    default_detail = 'Data processing failed.'
    default_code = 'data_processing_failed'

    def __init__(self, message=None, extra=None):
        """Initialize the exception with an optional message and extra details."""
        self.message = message or self.default_detail
        self.extra = extra
        super().__init__(detail=self.message)

class FileWriteException(APIException):
    """APIException subclass for tracking failures during payload serialization and cloud storage uploads."""
    status_code = 500
    default_detail = 'File write failed.'
    default_code = 'file_write_failed'

    def __init__(self, message=None, extra=None):
        """Initialize the exception with an optional message and extra details."""
        self.message = message or self.default_detail
        self.extra = extra
        super().__init__(detail=self.message)

class DatabaseException(APIException):
    """APIException subclass for tracking failures related to database queries or transaction rollbacks."""
    status_code = 500
    default_detail = 'Database connection or query failed.'
    default_code = 'database_error'

    def __init__(self, message=None, extra=None):
        """Initialize the exception with an optional message and extra details."""
        self.message = message or self.default_detail
        self.extra = extra
        super().__init__(detail=self.message)
