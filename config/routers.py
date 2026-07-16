class XBytesDataRouter:
    """
    A router to control all database operations on models in the
    market_data application for the xbytesdata database.
    """
    def db_for_read(self, model, **hints):
        if model._meta.model_name == 'product':
            return 'xbytesdata'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.model_name == 'product':
            return 'xbytesdata'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'xbytesdata':
            return model_name == 'product'
        elif model_name == 'product':
            return False
        return None
