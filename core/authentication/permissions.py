class AppPermissions:
    # Identity & Access Management (IAM)
    READ_USER = "READ_USER"
    CREATE_USER = "CREATE_USER"
    UPDATE_USER = "UPDATE_USER"
    DELETE_USER = "DELETE_USER"
    READ_ORGANIZATION = "READ_ORGANIZATION"
    MANAGE_ORGANIZATION = "MANAGE_ORGANIZATION"

    # Core Taxonomy & Integrations
    READ_BRAND = "READ_BRAND"
    MANAGE_BRAND = "MANAGE_BRAND"
    READ_TAXONOMY = "READ_TAXONOMY"
    MANAGE_TAXONOMY = "MANAGE_TAXONOMY"
    READ_INTEGRATIONS = "READ_INTEGRATIONS"
    MANAGE_INTEGRATIONS = "MANAGE_INTEGRATIONS"

    # Market Data & Catalog
    READ_PRODUCTS = "READ_PRODUCTS"
    UPDATE_PRODUCTS = "UPDATE_PRODUCTS"
    DELETE_PRODUCTS = "DELETE_PRODUCTS"
    VIEW_ANALYTICS = "VIEW_ANALYTICS"

    # Executions & Workflows
    READ_EXECUTIONS = "READ_EXECUTIONS"
    START_EXECUTION = "START_EXECUTION"
    STOP_EXECUTION = "STOP_EXECUTION"
    MANAGE_SCHEDULERS = "MANAGE_SCHEDULERS"
    READ_TASKS = "READ_TASKS"

PERMISSION_REGISTRY = [
    # IAM
    {"id": AppPermissions.READ_USER, "name": "Read Users", "group": "IAM", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.CREATE_USER, "name": "Create Users", "group": "IAM", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.UPDATE_USER, "name": "Update Users", "group": "IAM", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.DELETE_USER, "name": "Delete Users", "group": "IAM", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.READ_ORGANIZATION, "name": "Read Organizations", "group": "IAM", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.MANAGE_ORGANIZATION, "name": "Manage Organizations", "group": "IAM", "scopes": ["ORGANIZATION"]},

    # Taxonomy & Integrations
    {"id": AppPermissions.READ_BRAND, "name": "Read Brands", "group": "Taxonomy", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.MANAGE_BRAND, "name": "Manage Brands", "group": "Taxonomy", "scopes": ["INTERNAL"]},
    {"id": AppPermissions.READ_TAXONOMY, "name": "Read Taxonomy", "group": "Taxonomy", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.MANAGE_TAXONOMY, "name": "Manage Taxonomy", "group": "Taxonomy", "scopes": ["INTERNAL"]},
    {"id": AppPermissions.READ_INTEGRATIONS, "name": "Read Integrations", "group": "Integrations", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.MANAGE_INTEGRATIONS, "name": "Manage Integrations", "group": "Integrations", "scopes": ["INTERNAL"]},

    # Market Data
    {"id": AppPermissions.READ_PRODUCTS, "name": "Read Products", "group": "Market Data", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.UPDATE_PRODUCTS, "name": "Update Products", "group": "Market Data", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.DELETE_PRODUCTS, "name": "Delete Products", "group": "Market Data", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.VIEW_ANALYTICS, "name": "View Analytics", "group": "Market Data", "scopes": ["INTERNAL", "ORGANIZATION"]},

    # Executions
    {"id": AppPermissions.READ_EXECUTIONS, "name": "Read Executions", "group": "Executions", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.START_EXECUTION, "name": "Start Execution", "group": "Executions", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.STOP_EXECUTION, "name": "Stop Execution", "group": "Executions", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.MANAGE_SCHEDULERS, "name": "Manage Schedulers", "group": "Executions", "scopes": ["INTERNAL", "ORGANIZATION"]},
    {"id": AppPermissions.READ_TASKS, "name": "Read Tasks", "group": "Executions", "scopes": ["INTERNAL", "ORGANIZATION"]},
]
