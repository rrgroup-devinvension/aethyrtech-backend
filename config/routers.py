class XBytesDataRouter:
    """A router to control all database operations on models in the market_data application.

    This router is for the xbytesdata database.
    """
    def db_for_read(self, model, **hints):
        """DB for read."""
        if model._meta.model_name in ('product', 'xbytesproduct'):
            return 'xbytesdata'
        return None

    def db_for_write(self, model, **hints):
        """DB for write."""
        if model._meta.model_name in ('product', 'xbytesproduct'):
            return 'xbytesdata'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relation."""
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Allow migrate."""
        if db == 'xbytesdata':
            return model_name in ('product', 'xbytesproduct')
        elif model_name in ('product', 'xbytesproduct'):
            return False
        return None
