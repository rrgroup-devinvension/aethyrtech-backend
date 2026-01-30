"""
Centralized scheduler exception definitions.
All business layer exceptions must extend SchedulerBaseException.
"""

class SchedulerBaseException(Exception):

    default_message = "Something went wrong"
    error_code = "UNKNOWN_ERROR"

    def __init__(self, message=None, extra=None):

        self.user_message = message or self.default_message
        super().__init__(self.user_message)

        self.extra = extra


class ExternalAPIException(SchedulerBaseException):
    default_message = "External API failed"
    error_code = "API_ERROR"


class DataProcessingException(SchedulerBaseException):
    default_message = "Data processing failed"
    error_code = "DATA_ERROR"


class FileWriteException(SchedulerBaseException):
    default_message = "File write failed"
    error_code = "FILE_ERROR"


class DatabaseException(SchedulerBaseException):
    default_message = "Database operation failed"
    error_code = "DB_ERROR"
