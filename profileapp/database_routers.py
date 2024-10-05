class DatabaseRouter:
    """
    A router to control all database operations on models for the respective databases,
    with a fallback to 'local_db' if 'default' (server_db) is unreachable.
    """

    def db_for_read(self, model, **hints):
        # Attempt to read from 'default' (server_db) and fallback to 'local' on failure
        print(model._meta.app_label)
        if model._meta.app_label == 'profileapp':
            try:
                # Attempt a connection to 'default' (server_db)
                from django.db import connections
                connections['default'].cursor()  # This will throw an error if the server DB is unreachable
                return 'default'
            except Exception:
                # Fallback to 'local_db' if the server DB is unreachable
                return 'local'
        return 'local'

    def db_for_write(self, model, **hints):
        # Attempt to write to 'default' (server_db) and fallback to 'local' on failure
        if model._meta.app_label == 'profileapp':
            try:
                # Attempt a connection to 'default' (server_db)
                from django.db import connections
                connections['default'].cursor()  # This will throw an error if the server DB is unreachable
                return 'default'
            except Exception:
                # Fallback to 'local' if the server DB is unreachable
                return 'local'
        return 'local'

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure migrations are applied to both 'default' (server_db) and 'local'.
        """
        if app_label == 'profileapp':
            return db == 'default' or db == 'local'
        return db == 'local'