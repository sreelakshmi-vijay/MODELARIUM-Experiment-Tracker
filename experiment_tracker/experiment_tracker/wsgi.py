"""
WSGI config for experiment_tracker project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os  # Provides access to environment variables and system functions

from django.core.wsgi import get_wsgi_application  # Creates the WSGI application object

# Sets the default settings module for the Django project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'experiment_tracker.settings')

# WSGI application used by WSGI servers (e.g., Gunicorn, uWSGI)
application = get_wsgi_application()
