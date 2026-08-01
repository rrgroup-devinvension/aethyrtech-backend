from typing import ClassVar


class ExternalDBRouter:
    """Intelligent database router for delegating operations to segregated external databases.

    Ensures that data bound for vendor-specific secondary databases (e.g., XBytes, Karmatech)
    are strictly isolated from the primary system database, intercepting all read, write,
    relation, and migration requests emitted by the `market_integrations` models.
    """
    route_app_labels: ClassVar[set[str]] = {'market_integrations'}

    def db_for_read(self, model, **hints):
        """Route database read operations to the corresponding external vendor database.

        Analyzes the target model's namespace prefix to map it securely to its configured
        database alias (e.g., 'xbytes_db' or 'karmatech_db') for isolated extraction.
        """
        if model._meta.app_label in self.route_app_labels:
            if model.__name__.startswith('XBytes'):
                return 'xbytes_db'
            elif model.__name__.startswith('Karmatech'):
                return 'karmatech_db'
        return None

    def db_for_write(self, model, **hints):
        """Route database write operations to the corresponding external vendor database.

        Intercepts save/update commands for `market_integrations` models, pushing the payload
        exclusively into the targeted secondary database alias to protect the primary schema.
        """
        if model._meta.app_label in self.route_app_labels:
            if model.__name__.startswith('XBytes'):
                return 'xbytes_db'
            elif model.__name__.startswith('Karmatech'):
                return 'karmatech_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Validate foreign key relationships across disparate database schemas.

        Enforces strict boundary conditions by permitting model relations only if both
        objects definitively reside within the identical external database cluster.
        """
        if (
            obj1._meta.app_label in self.route_app_labels or
            obj2._meta.app_label in self.route_app_labels
        ):
            # Only allow if they are meant for the same external db
            db1 = self.db_for_read(obj1.__class__)
            db2 = self.db_for_read(obj2.__class__)
            return db1 == db2
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Intercept Django migration commands to restrict schema synchronization.

        Acts as a strict gateway to ensure that:
        1. Vendor integration models migrate EXCLUSIVELY to their respective external DBs.
        2. Core platform models are BLOCKED from polluting the external vendor DBs.
        """
        if app_label in self.route_app_labels:
            if model_name:
                if model_name.startswith('xbytes'):
                    return db == 'xbytes_db'
                elif model_name.startswith('karmatech'):
                    return db == 'karmatech_db'
            # Default fallback for market_integrations app: NO migrations outside of target DBs
            return False

        # For all other apps, prevent them from migrating onto our external DBs
        if db in ['xbytes_db', 'karmatech_db']:
            return False

        return None
