from django.apps import AppConfig  # Base class for Django application configuration


class ExptWebappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # Default primary key type for models in this app
    name = 'expt_webapp'  # Your Django app