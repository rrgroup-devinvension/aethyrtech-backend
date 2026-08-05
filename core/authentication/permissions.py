class AppPermissions:
    """App permissions."""
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

    # Extended Sidebar Permissions
    READ_ROLES = "READ_ROLES"
    CREATE_ROLE = "CREATE_ROLE"
    UPDATE_ROLE = "UPDATE_ROLE"
    DELETE_ROLE = "DELETE_ROLE"
    READ_CATEGORIES = "READ_CATEGORIES"
    CREATE_CATEGORY = "CREATE_CATEGORY"
    UPDATE_CATEGORY = "UPDATE_CATEGORY"
    DELETE_CATEGORY = "DELETE_CATEGORY"

    READ_PLATFORMS = "READ_PLATFORMS"
    CREATE_PLATFORM = "CREATE_PLATFORM"
    UPDATE_PLATFORM = "UPDATE_PLATFORM"
    DELETE_PLATFORM = "DELETE_PLATFORM"

    READ_API_PROVIDERS = "READ_API_PROVIDERS"
    CREATE_API_PROVIDER = "CREATE_API_PROVIDER"
    UPDATE_API_PROVIDER = "UPDATE_API_PROVIDER"
    DELETE_API_PROVIDER = "DELETE_API_PROVIDER"

    READ_LLM_PROVIDERS = "READ_LLM_PROVIDERS"
    CREATE_LLM_PROVIDER = "CREATE_LLM_PROVIDER"
    UPDATE_LLM_PROVIDER = "UPDATE_LLM_PROVIDER"
    DELETE_LLM_PROVIDER = "DELETE_LLM_PROVIDER"

    READ_JSON_TEMPLATES = "READ_JSON_TEMPLATES"
    CREATE_JSON_TEMPLATE = "CREATE_JSON_TEMPLATE"
    UPDATE_JSON_TEMPLATE = "UPDATE_JSON_TEMPLATE"
    DELETE_JSON_TEMPLATE = "DELETE_JSON_TEMPLATE"
    READ_JSON_GENERATION = "READ_JSON_GENERATION"
    READ_MARKET_DATA_DUMP = "READ_MARKET_DATA_DUMP"
    READ_SCHEDULERS = "READ_SCHEDULERS"
    CREATE_SCHEDULER = "CREATE_SCHEDULER"
    UPDATE_SCHEDULER = "UPDATE_SCHEDULER"
    DELETE_SCHEDULER = "DELETE_SCHEDULER"


    READ_GEN_INSIGHTS = "READ_GEN_INSIGHTS"
    READ_EXPERIANCE_DASHBOARD = "READ_EXPERIANCE_DASHBOARD"
    READ_RISK_CENTER = "READ_RISK_CENTER"
    READ_GROWTH_LEVER = "READ_GROWTH_LEVER"
    READ_CRO_BARRIERS = "READ_CRO_BARRIERS"
    READ_GAP_LANDSCAPES = "READ_GAP_LANDSCAPES"
    READ_PLATFORM_AUDIT = "READ_PLATFORM_AUDIT"
    READ_AUDIENCE_AUDIT = "READ_AUDIENCE_AUDIT"



PERMISSION_REGISTRY = [
    # IAM
    {
        "id": AppPermissions.READ_USER,
        "name": "Read Users",
        "group": "IAM",
        "scopes": ["INTERNAL"],
        "description": "View users and their details.",
        "implies": [],
    },
    {
        "id": AppPermissions.CREATE_USER,
        "name": "Create Users",
        "group": "IAM",
        "scopes": ["INTERNAL"],
        "description": "Create new users in the system.",
        "implies": [AppPermissions.READ_USER],
    },
    {
        "id": AppPermissions.UPDATE_USER,
        "name": "Update Users",
        "group": "IAM",
        "scopes": ["INTERNAL"],
        "description": "Modify existing user profiles.",
        "implies": [AppPermissions.READ_USER],
    },
    {
        "id": AppPermissions.DELETE_USER,
        "name": "Delete Users",
        "group": "IAM",
        "scopes": ["INTERNAL"],
        "description": "Remove users from the system.",
        "implies": [AppPermissions.READ_USER],
    },
    {
        "id": AppPermissions.READ_ORGANIZATION,
        "name": "Read Organizations",
        "group": "IAM",
        "scopes": ["INTERNAL"],
        "description": "View organizational details.",
        "implies": [],
    },
    {
        "id": AppPermissions.MANAGE_ORGANIZATION,
        "name": "Manage Organizations",
        "group": "IAM",
        "scopes": ["INTERNAL"],
        "description": "Create, edit, and delete organizations.",
        "implies": [AppPermissions.READ_ORGANIZATION],
    },

    # Taxonomy & Integrations
    {
        "id": AppPermissions.READ_BRAND,
        "name": "Read Brands",
        "group": "Taxonomy",
        "scopes": ["INTERNAL"],
        "description": "View brand information.",
        "implies": [],
    },
    {
        "id": AppPermissions.MANAGE_BRAND,
        "name": "Manage Brands",
        "group": "Taxonomy",
        "scopes": ["INTERNAL"],
        "description": "Full access to modify brands.",
        "implies": [AppPermissions.READ_BRAND],
    },
    {
        "id": AppPermissions.READ_TAXONOMY,
        "name": "Read Taxonomy",
        "group": "Taxonomy",
        "scopes": ["INTERNAL"],
        "description": "View taxonomy structures.",
        "implies": [],
    },
    {
        "id": AppPermissions.MANAGE_TAXONOMY,
        "name": "Manage Taxonomy",
        "group": "Taxonomy",
        "scopes": ["INTERNAL"],
        "description": "Full access to modify taxonomy.",
        "implies": [AppPermissions.READ_TAXONOMY],
    },
    {
        "id": AppPermissions.READ_INTEGRATIONS,
        "name": "Read Integrations",
        "group": "Integrations",
        "scopes": ["INTERNAL"],
        "description": "View connected integrations.",
        "implies": [],
    },
    {
        "id": AppPermissions.MANAGE_INTEGRATIONS,
        "name": "Manage Integrations",
        "group": "Integrations",
        "scopes": ["INTERNAL"],
        "description": "Configure and manage integrations.",
        "implies": [AppPermissions.READ_INTEGRATIONS],
    },

    # Market Data
    {
        "id": AppPermissions.READ_PRODUCTS,
        "name": "Read Products",
        "group": "Market Data",
        "scopes": ["INTERNAL"],
        "description": "View product catalog.",
        "implies": [],
    },
    {
        "id": AppPermissions.UPDATE_PRODUCTS,
        "name": "Update Products",
        "group": "Market Data",
        "scopes": ["INTERNAL"],
        "description": "Modify existing products.",
        "implies": [AppPermissions.READ_PRODUCTS],
    },
    {
        "id": AppPermissions.DELETE_PRODUCTS,
        "name": "Delete Products",
        "group": "Market Data",
        "scopes": ["INTERNAL"],
        "description": "Remove products from catalog.",
        "implies": [AppPermissions.READ_PRODUCTS],
    },
    {
        "id": AppPermissions.VIEW_ANALYTICS,
        "name": "View Analytics",
        "group": "Market Data",
        "scopes": ["INTERNAL"],
        "description": "Access market analytics dashboards.",
        "implies": [],
    },

    # Executions
    {
        "id": AppPermissions.READ_EXECUTIONS,
        "name": "Read Executions",
        "group": "Executions",
        "scopes": ["INTERNAL"],
        "description": "View execution logs and history.",
        "implies": [],
    },
    {
        "id": AppPermissions.START_EXECUTION,
        "name": "Start Execution",
        "group": "Executions",
        "scopes": ["INTERNAL"],
        "description": "Initiate new executions.",
        "implies": [AppPermissions.READ_EXECUTIONS],
    },
    {
        "id": AppPermissions.STOP_EXECUTION,
        "name": "Stop Execution",
        "group": "Executions",
        "scopes": ["INTERNAL"],
        "description": "Halt running executions.",
        "implies": [AppPermissions.READ_EXECUTIONS],
    },
    {
        "id": AppPermissions.MANAGE_SCHEDULERS,
        "name": "Manage Schedulers",
        "group": "Executions",
        "scopes": ["INTERNAL"],
        "description": "Configure execution schedulers.",
        "implies": [AppPermissions.READ_EXECUTIONS],
    },
    {
        "id": AppPermissions.READ_TASKS,
        "name": "Read Tasks",
        "group": "Executions",
        "scopes": ["INTERNAL"],
        "description": "View background task queue.",
        "implies": [],
    },

    # Roles
    {
        "id": AppPermissions.READ_ROLES,
        "name": "Read Roles",
        "group": "IAM",
        "scopes": ["INTERNAL"],
        "description": "View roles and their permissions.",
        "implies": [],
    },
    {
        "id": AppPermissions.CREATE_ROLE,
        "name": "Create Roles",
        "group": "IAM",
        "scopes": ["INTERNAL"],
        "description": "Create new custom roles.",
        "implies": [AppPermissions.READ_ROLES],
    },
    {
        "id": AppPermissions.UPDATE_ROLE,
        "name": "Update Roles",
        "group": "IAM",
        "scopes": ["INTERNAL"],
        "description": "Modify existing roles and permissions.",
        "implies": [AppPermissions.READ_ROLES],
    },
    {
        "id": AppPermissions.DELETE_ROLE,
        "name": "Delete Roles",
        "group": "IAM",
        "scopes": ["INTERNAL"],
        "description": "Delete custom roles.",
        "implies": [AppPermissions.READ_ROLES],
    },


    # Configuration & Setup
    {
        "id": AppPermissions.READ_CATEGORIES,
        "name": "Read Categories",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "View content categories.",
        "implies": [],
    },
    {
        "id": AppPermissions.CREATE_CATEGORY,
        "name": "Create Categories",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Create new categories.",
        "implies": [AppPermissions.READ_CATEGORIES],
    },
    {
        "id": AppPermissions.UPDATE_CATEGORY,
        "name": "Update Categories",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Modify existing categories.",
        "implies": [AppPermissions.READ_CATEGORIES],
    },
    {
        "id": AppPermissions.DELETE_CATEGORY,
        "name": "Delete Categories",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Delete categories.",
        "implies": [AppPermissions.READ_CATEGORIES],
    },

    {
        "id": AppPermissions.READ_PLATFORMS,
        "name": "Read Platforms",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "View integrated platforms.",
        "implies": [],
    },
    {
        "id": AppPermissions.CREATE_PLATFORM,
        "name": "Create Platforms",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Create new platforms.",
        "implies": [AppPermissions.READ_PLATFORMS],
    },
    {
        "id": AppPermissions.UPDATE_PLATFORM,
        "name": "Update Platforms",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Modify existing platforms.",
        "implies": [AppPermissions.READ_PLATFORMS],
    },
    {
        "id": AppPermissions.DELETE_PLATFORM,
        "name": "Delete Platforms",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Delete platforms.",
        "implies": [AppPermissions.READ_PLATFORMS],
    },

    {
        "id": AppPermissions.READ_API_PROVIDERS,
        "name": "Read API Providers",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "View API provider configurations.",
        "implies": [],
    },
    {
        "id": AppPermissions.CREATE_API_PROVIDER,
        "name": "Create API Providers",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Create new API providers.",
        "implies": [AppPermissions.READ_API_PROVIDERS],
    },
    {
        "id": AppPermissions.UPDATE_API_PROVIDER,
        "name": "Update API Providers",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Modify existing API providers.",
        "implies": [AppPermissions.READ_API_PROVIDERS],
    },
    {
        "id": AppPermissions.DELETE_API_PROVIDER,
        "name": "Delete API Providers",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Delete API providers.",
        "implies": [AppPermissions.READ_API_PROVIDERS],
    },

    {
        "id": AppPermissions.READ_LLM_PROVIDERS,
        "name": "Read LLM Providers",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "View Large Language Model configurations.",
        "implies": [],
    },
    {
        "id": AppPermissions.CREATE_LLM_PROVIDER,
        "name": "Create LLM Providers",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Create new LLM providers.",
        "implies": [AppPermissions.READ_LLM_PROVIDERS],
    },
    {
        "id": AppPermissions.UPDATE_LLM_PROVIDER,
        "name": "Update LLM Providers",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Modify existing LLM providers.",
        "implies": [AppPermissions.READ_LLM_PROVIDERS],
    },
    {
        "id": AppPermissions.DELETE_LLM_PROVIDER,
        "name": "Delete LLM Providers",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Delete LLM providers.",
        "implies": [AppPermissions.READ_LLM_PROVIDERS],
    },

    {
        "id": AppPermissions.READ_JSON_TEMPLATES,
        "name": "Read JSON Templates",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "View data output templates.",
        "implies": [],
    },
    {
        "id": AppPermissions.CREATE_JSON_TEMPLATE,
        "name": "Create JSON Templates",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Create new JSON templates.",
        "implies": [AppPermissions.READ_JSON_TEMPLATES],
    },
    {
        "id": AppPermissions.UPDATE_JSON_TEMPLATE,
        "name": "Update JSON Templates",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Modify existing JSON templates.",
        "implies": [AppPermissions.READ_JSON_TEMPLATES],
    },
    {
        "id": AppPermissions.DELETE_JSON_TEMPLATE,
        "name": "Delete JSON Templates",
        "group": "Configuration",
        "scopes": ["INTERNAL"],
        "description": "Delete JSON templates.",
        "implies": [AppPermissions.READ_JSON_TEMPLATES],
    },

    # Intelligence & Insights
    {
        "id": AppPermissions.READ_JSON_GENERATION,
        "name": "Read JSON Generation",
        "group": "Insights",
        "scopes": ["INTERNAL"],
        "description": "View JSON generation features.",
        "implies": [],
    },
    {
        "id": AppPermissions.READ_MARKET_DATA_DUMP,
        "name": "Read Market Data Dump",
        "group": "Insights",
        "scopes": ["INTERNAL"],
        "description": "Access raw market data exports.",
        "implies": [],
    },
    {
        "id": AppPermissions.READ_SCHEDULERS,
        "name": "Read Schedulers",
        "group": "Insights",
        "scopes": ["INTERNAL"],
        "description": "View execution schedules.",
        "implies": [],
    },
    {
        "id": AppPermissions.CREATE_SCHEDULER,
        "name": "Create Schedulers",
        "group": "Insights",
        "scopes": ["INTERNAL"],
        "description": "Create new schedules.",
        "implies": [AppPermissions.READ_SCHEDULERS],
    },
    {
        "id": AppPermissions.UPDATE_SCHEDULER,
        "name": "Update Schedulers",
        "group": "Insights",
        "scopes": ["INTERNAL"],
        "description": "Modify existing schedules.",
        "implies": [AppPermissions.READ_SCHEDULERS],
    },
    {
        "id": AppPermissions.DELETE_SCHEDULER,
        "name": "Delete Schedulers",
        "group": "Insights",
        "scopes": ["INTERNAL"],
        "description": "Delete schedules.",
        "implies": [AppPermissions.READ_SCHEDULERS],
    },
    {
        "id": AppPermissions.READ_AUDIENCE_AUDIT,
        "name": "Read Audience Audit",
        "group": "Experiance Cloud",
        "scopes": ["ORGANIZATION"],
        "description": "View audience demographic audits.",
        "implies": [],
    },
    {
        "id": AppPermissions.READ_AUDIENCE_AUDIT,
        "name": "Read Audience Audit",
        "group": "Experiance Cloud",
        "scopes": ["ORGANIZATION"],
        "description": "View audience demographic audits.",
        "implies": [],
    },
    {
        "id": AppPermissions.READ_GEN_INSIGHTS,
        "name": "Read Gen Insights",
        "group": "Experiance Cloud",
        "scopes": [ "ORGANIZATION"],
        "description": "Access AI-generated market insights.",
        "implies": [],
    },
    {
        "id": AppPermissions.READ_EXPERIANCE_DASHBOARD,
        "name": "Read Experience Dashboard",
        "group": "Experiance Cloud",
        "scopes": ["ORGANIZATION"],
        "description": "View digital experience metrics.",
        "implies": [],
    },
    {
        "id": AppPermissions.READ_RISK_CENTER,
        "name": "Read Risk Center",
        "group": "Experiance Cloud",
        "scopes": ["ORGANIZATION"],
        "description": "View risk analysis dashboards.",
        "implies": [],
    },
    {
        "id": AppPermissions.READ_GROWTH_LEVER,
        "name": "Read Growth Lever",
        "group": "Experiance Cloud",
        "scopes": ["ORGANIZATION"],
        "description": "View growth opportunity analysis.",
        "implies": [],
    },
    {
        "id": AppPermissions.READ_CRO_BARRIERS,
        "name": "Read CRO Barriers",
        "group": "Experiance Cloud",
        "scopes": ["ORGANIZATION"],
        "description": "View conversion rate optimization data.",
        "implies": [],
    },
    {
        "id": AppPermissions.READ_GAP_LANDSCAPES,
        "name": "Read Gap Landscapes",
        "group": "Experiance Cloud",
        "scopes": ["ORGANIZATION"],
        "description": "View competitive gap analysis.",
        "implies": [],
    },
    {
        "id": AppPermissions.READ_PLATFORM_AUDIT,
        "name": "Read Platform Audit",
        "group": "Experiance Cloud",
        "scopes": ["ORGANIZATION"],
        "description": "View technical platform audits.",
        "implies": [],
    },

]
