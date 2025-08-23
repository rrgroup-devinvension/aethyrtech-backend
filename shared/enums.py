from enum import Enum

class StatusEnum(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

class RoleEnum(str, Enum):
    USER = "user"
    ADMIN = "admin"
    STAFF = "staff"
