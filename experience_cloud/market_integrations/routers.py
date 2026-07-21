class ExternalDBRouter:
    """
    A router to control all database operations on models in the
    market_integrations application.
    """
    route_app_labels = {'market_integrations'}

    def db_for_read(self, model, **hints):
        """
        Attempts to read market_integrations models go to their respective external DB.
        """
        if model._meta.app_label in self.route_app_labels:
            if model.__name__.startswith('XBytes'):
                return 'xbytes_db'
            elif model.__name__.startswith('Karmatech'):
                return 'karmatech_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write market_integrations models go to their respective external DB.
        """
        if model._meta.app_label in self.route_app_labels:
            if model.__name__.startswith('XBytes'):
                return 'xbytes_db'
            elif model.__name__.startswith('Karmatech'):
                return 'karmatech_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the market_integrations app is
        involved with another model in the SAME external db.
        """
        if (
            obj1._meta.app_label in self.route_app_labels or
            obj2._meta.app_label in self.route_app_labels
        ):
            # Only allow if they are meant for the same external db
            db1 = self.db_for_read(obj1.__class__)
            db2 = self.db_for_read(obj2.__class__)
            if db1 == db2:
                return True
            return False
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the market_integrations apps only appear in the
        'xbytes_db' and 'karmatech_db' databases.
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
