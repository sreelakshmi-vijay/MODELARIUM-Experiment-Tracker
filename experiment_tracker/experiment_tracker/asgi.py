"""
ASGI config for experiment_tracker project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os  # Provides access to environment variables and OS-level functions

from django.core.asgi import get_asgi_application  # Creates the ASGI application object

# Sets the default settings module for the Django project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'experiment_tracker.settings')

# Creates the ASGI application callable used by ASGI servers (e.g., Uvicorn, Daphne)
application = get_asgi_application()
